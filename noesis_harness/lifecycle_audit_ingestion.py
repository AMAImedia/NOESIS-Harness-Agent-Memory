"""Durable import of verified lifecycle audit bundles.

Patterns adapted from OperatorIngestionLedger, signed report bundles, lifecycle
verification, and fail-closed external evidence ingestion. This adapter never
executes providers and never converts audit events into execution evidence.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import threading
import time
from contextlib import closing
from pathlib import Path
from typing import Any, Mapping

from .report_bundle import verify_report_bundle
from .report_export_lifecycle import lifecycle_audit_readiness

SCHEMA = "noesis.lifecycle-audit-ingestion.v1"
STATES = frozenset({"preflight", "awaiting_approval", "approved", "imported", "blocked", "rejected"})


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(value), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def _sign(value: Mapping[str, Any], key: bytes) -> str:
    return hmac.new(key, _canonical(value), hashlib.sha256).hexdigest()


class LifecycleAuditIngestionError(ValueError):
    """Raised when lifecycle audit import fails closed."""


class LifecycleAuditIngestionAdapter:
    def __init__(self, ledger_path: str | Path, *, signing_key: bytes, max_age_seconds: float = 86400.0):
        if not isinstance(signing_key, bytes) or len(signing_key) < 16:
            raise ValueError("signing_key_too_short")
        if max_age_seconds <= 0:
            raise ValueError("max_age_seconds_invalid")
        self.path = Path(ledger_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.signing_key = signing_key
        self.max_age_seconds = float(max_age_seconds)
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("CREATE TABLE IF NOT EXISTS lifecycle_imports (sequence INTEGER PRIMARY KEY AUTOINCREMENT, record_id TEXT NOT NULL, state TEXT NOT NULL, payload TEXT NOT NULL, created_at REAL NOT NULL)")
            db.commit()

    def _append(self, record_id: str, state: str, payload: Mapping[str, Any]) -> None:
        if state not in STATES:
            raise LifecycleAuditIngestionError("invalid_state")
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("INSERT INTO lifecycle_imports(record_id,state,payload,created_at) VALUES(?,?,?,?)", (record_id, state, json.dumps(dict(payload), sort_keys=True, ensure_ascii=False), time.time()))
            db.commit()

    def _latest(self, record_id: str) -> tuple[str, dict[str, Any]] | None:
        with closing(sqlite3.connect(self.path)) as db:
            row = db.execute("SELECT state,payload FROM lifecycle_imports WHERE record_id=? ORDER BY sequence DESC LIMIT 1", (record_id,)).fetchone()
        return (str(row[0]), json.loads(row[1])) if row else None

    def _record_exists_for_digest(self, bundle_digest: str) -> bool:
        with closing(sqlite3.connect(self.path)) as db:
            return db.execute("SELECT 1 FROM lifecycle_imports WHERE json_extract(payload, '$.bundle_digest')=? LIMIT 1", (bundle_digest,)).fetchone() is not None

    def preflight(self, bundle_path: str | Path, lifecycle_path: str | Path, *, now: float | None = None) -> Mapping[str, Any]:
        bundle_result = verify_report_bundle(bundle_path, self.signing_key)
        if bundle_result.get("status") != "passed":
            return {"schema_version": SCHEMA, "state": "blocked", "reason": "bundle_verification:" + str(bundle_result.get("reason", "failed")), "execution_allowed": False, "automatic_execution": False, "claim": False}
        lifecycle_result = lifecycle_audit_readiness(lifecycle_path, self.signing_key)
        if lifecycle_result.get("status") != "passed":
            return {"schema_version": SCHEMA, "state": "blocked", "reason": "lifecycle_verification:" + str(lifecycle_result.get("reason", "failed")), "execution_allowed": False, "automatic_execution": False, "claim": False}
        current = time.time() if now is None else float(now)
        age = current - max(Path(bundle_path).stat().st_mtime, Path(lifecycle_path).stat().st_mtime)
        if age < 0 or age > self.max_age_seconds:
            return {"schema_version": SCHEMA, "state": "blocked", "reason": "evidence_stale", "age_seconds": age, "execution_allowed": False, "automatic_execution": False, "claim": False}
        bundle_digest = str(bundle_result["bundle_digest"])
        if self._record_exists_for_digest(bundle_digest):
            return {"schema_version": SCHEMA, "state": "blocked", "reason": "duplicate_bundle_digest", "bundle_digest": bundle_digest, "execution_allowed": False, "automatic_execution": False, "claim": False}
        record_id = "lifecycle-import-" + _digest({"bundle_digest": bundle_digest, "audit_digest": lifecycle_result.get("audit_digest")})[:24]
        payload = {"schema_version": SCHEMA, "record_id": record_id, "bundle_digest": bundle_digest, "audit_digest": lifecycle_result.get("audit_digest", ""), "event_count": lifecycle_result.get("event_count", 0), "state": "awaiting_approval", "execution_allowed": False, "automatic_execution": False, "claim": False, "execution_claim": False, "comparative_claim": False, "reason": "awaiting_explicit_operator_approval"}
        self._append(record_id, "awaiting_approval", payload)
        return payload

    def approve(self, record_id: str, *, operator_id: str, ttl_seconds: float = 300.0, now: float | None = None) -> Mapping[str, Any]:
        latest = self._latest(record_id)
        if latest is None or latest[0] != "awaiting_approval":
            raise LifecycleAuditIngestionError("approval_not_allowed")
        issued = time.time() if now is None else float(now)
        approval = {"schema_version": SCHEMA, "record_id": record_id, "operator_id": str(operator_id), "issued_at": issued, "expires_at": issued + float(ttl_seconds), "bundle_digest": latest[1].get("bundle_digest"), "audit_digest": latest[1].get("audit_digest"), "execution_allowed": False, "automatic_execution": False, "claim": False}
        receipt = {**approval, "signature": _sign(approval, self.signing_key)}
        self._append(record_id, "approved", {**latest[1], "approval": receipt})
        return receipt

    def import_approved(self, record_id: str, approval: Mapping[str, Any], *, now: float | None = None) -> Mapping[str, Any]:
        latest = self._latest(record_id)
        if latest is None or latest[0] != "approved":
            raise LifecycleAuditIngestionError("import_requires_approved_record")
        expected = {name: approval.get(name) for name in ("schema_version", "record_id", "operator_id", "issued_at", "expires_at", "bundle_digest", "audit_digest", "execution_allowed", "automatic_execution", "claim")}
        if not hmac.compare_digest(str(approval.get("signature", "")), _sign(expected, self.signing_key)):
            self._append(record_id, "rejected", {**latest[1], "reason": "approval_signature_invalid"})
            raise LifecycleAuditIngestionError("approval_signature_invalid")
        current = time.time() if now is None else float(now)
        if float(approval.get("expires_at", 0)) <= current or approval.get("record_id") != record_id or approval.get("bundle_digest") != latest[1].get("bundle_digest") or approval.get("audit_digest") != latest[1].get("audit_digest"):
            self._append(record_id, "rejected", {**latest[1], "reason": "approval_stale_or_identity_mismatch"})
            raise LifecycleAuditIngestionError("approval_stale_or_identity_mismatch")
        result = {"status": "accepted_audit_only", "record_id": record_id, "bundle_digest": latest[1].get("bundle_digest"), "audit_digest": latest[1].get("audit_digest"), "claim": False, "execution_claim": False, "comparative_claim": False, "claim_boundary": "lifecycle_audit_only"}
        self._append(record_id, "imported", {**latest[1], "result": result})
        return {"schema_version": SCHEMA, "record_id": record_id, "state": "imported", "result": result, "execution_allowed": False, "automatic_execution": False, "claim": False}

    def status(self, record_id: str) -> Mapping[str, Any]:
        latest = self._latest(record_id)
        if latest is None:
            return {"schema_version": SCHEMA, "record_id": record_id, "state": "not_found", "available": False}
        return {"schema_version": SCHEMA, "record_id": record_id, "state": latest[0], "available": True, "execution_allowed": False, "automatic_execution": False, "claim": False, "reason": latest[1].get("reason", "")}


def build_healthserver_wiring(adapter: LifecycleAuditIngestionAdapter):
    """Return a status provider and operator action handler for HealthServer."""
    current_record = {"record_id": ""}
    lock = threading.RLock()

    def status_provider() -> Mapping[str, Any]:
        with lock:
            record_id = current_record["record_id"]
        if not record_id:
            return {"schema_version": SCHEMA, "state": "not_run", "available": False, "execution_allowed": False, "automatic_execution": False, "automatic_import": False, "claim": False, "control": "operator_approval_required"}
        return dict(adapter.status(record_id))

    def action_handler(payload: Mapping[str, Any], context: Any) -> Mapping[str, Any]:
        action = str(payload.get("action", ""))
        if action == "preflight":
            bundle_path = Path(str(payload.get("bundle_path", "")))
            lifecycle_path = Path(str(payload.get("lifecycle_path", "")))
            if not bundle_path.is_absolute() or not lifecycle_path.is_absolute() or not bundle_path.is_file() or not lifecycle_path.is_file():
                raise LifecycleAuditIngestionError("input_paths_must_be_existing_absolute_files")
            result = adapter.preflight(bundle_path, lifecycle_path)
            if result.get("record_id"):
                with lock:
                    current_record["record_id"] = str(result["record_id"])
            return result
        record_id = str(payload.get("record_id", ""))
        if not record_id:
            raise LifecycleAuditIngestionError("record_id_required")
        if action == "approve":
            result = adapter.approve(record_id, operator_id=str(context.operator_id), ttl_seconds=float(payload.get("ttl_seconds", 300.0)))
            return {"state": "approved", "record_id": record_id, "approval": result, "claim": False}
        if action == "import":
            approval = payload.get("approval")
            if not isinstance(approval, Mapping):
                raise LifecycleAuditIngestionError("approval_required")
            return adapter.import_approved(record_id, approval)
        raise LifecycleAuditIngestionError("unsupported_lifecycle_ingestion_action")

    return status_provider, action_handler


__all__ = ["SCHEMA", "STATES", "LifecycleAuditIngestionError", "LifecycleAuditIngestionAdapter", "build_healthserver_wiring"]
