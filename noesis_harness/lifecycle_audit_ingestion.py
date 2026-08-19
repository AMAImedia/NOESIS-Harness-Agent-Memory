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
import uuid
from contextlib import closing
from pathlib import Path
from typing import Any, Mapping

from .report_bundle import verify_report_bundle
from .report_export_lifecycle import lifecycle_audit_readiness

SCHEMA = "noesis.lifecycle-audit-ingestion.v1"
RECEIPT_SCHEMA = "noesis.lifecycle-audit-ingestion-receipt.v1"
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

    def preflight(self, bundle_path: str | Path, lifecycle_path: str | Path, *, now: float | None = None, operator_id: str = "", action_id: str | None = None) -> Mapping[str, Any]:
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
        action_id = str(action_id or "ingestion-action-" + uuid.uuid4().hex)
        payload = {"schema_version": SCHEMA, "record_id": record_id, "bundle_digest": bundle_digest, "audit_digest": lifecycle_result.get("audit_digest", ""), "event_count": lifecycle_result.get("event_count", 0), "state": "awaiting_approval", "execution_allowed": False, "automatic_execution": False, "claim": False, "execution_claim": False, "comparative_claim": False, "reason": "awaiting_explicit_operator_approval"}
        receipt = self._action_receipt(action_id, "preflight", operator_id, record_id, payload["state"], payload)
        self._append(record_id, "awaiting_approval", {**payload, "receipt": receipt})
        return {**payload, "receipt": receipt}

    def approve(self, record_id: str, *, operator_id: str, ttl_seconds: float = 300.0, now: float | None = None, action_id: str | None = None) -> Mapping[str, Any]:
        latest = self._latest(record_id)
        if latest is None or latest[0] != "awaiting_approval":
            raise LifecycleAuditIngestionError("approval_not_allowed")
        issued = time.time() if now is None else float(now)
        approval = {"schema_version": SCHEMA, "record_id": record_id, "operator_id": str(operator_id), "issued_at": issued, "expires_at": issued + float(ttl_seconds), "bundle_digest": latest[1].get("bundle_digest"), "audit_digest": latest[1].get("audit_digest"), "execution_allowed": False, "automatic_execution": False, "claim": False}
        receipt = {**approval, "signature": _sign(approval, self.signing_key)}
        action_receipt = self._action_receipt(str(action_id or "ingestion-action-" + uuid.uuid4().hex), "approve", operator_id, record_id, "approved", latest[1])
        self._append(record_id, "approved", {**latest[1], "approval": receipt, "receipt": action_receipt})
        return {**receipt, "receipt": action_receipt, "record_id": record_id, "state": "approved", "claim": False}

    def import_approved(self, record_id: str, approval: Mapping[str, Any], *, now: float | None = None, operator_id: str = "", action_id: str | None = None) -> Mapping[str, Any]:
        latest = self._latest(record_id)
        if latest is None or latest[0] != "approved":
            raise LifecycleAuditIngestionError("import_requires_approved_record")
        if isinstance(approval.get("approval"), Mapping):
            approval = approval["approval"]
        expected = {name: approval.get(name) for name in ("schema_version", "record_id", "operator_id", "issued_at", "expires_at", "bundle_digest", "audit_digest", "execution_allowed", "automatic_execution", "claim")}
        if not hmac.compare_digest(str(approval.get("signature", "")), _sign(expected, self.signing_key)):
            self._append(record_id, "rejected", {**latest[1], "reason": "approval_signature_invalid"})
            raise LifecycleAuditIngestionError("approval_signature_invalid")
        current = time.time() if now is None else float(now)
        if float(approval.get("expires_at", 0)) <= current or approval.get("record_id") != record_id or approval.get("bundle_digest") != latest[1].get("bundle_digest") or approval.get("audit_digest") != latest[1].get("audit_digest"):
            self._append(record_id, "rejected", {**latest[1], "reason": "approval_stale_or_identity_mismatch"})
            raise LifecycleAuditIngestionError("approval_stale_or_identity_mismatch")
        result = {"status": "accepted_audit_only", "record_id": record_id, "bundle_digest": latest[1].get("bundle_digest"), "audit_digest": latest[1].get("audit_digest"), "claim": False, "execution_claim": False, "comparative_claim": False, "claim_boundary": "lifecycle_audit_only"}
        action_receipt = self._action_receipt(str(action_id or "ingestion-action-" + uuid.uuid4().hex), "import", operator_id, record_id, "imported", latest[1])
        self._append(record_id, "imported", {**latest[1], "result": result, "receipt": action_receipt})
        return {"schema_version": SCHEMA, "record_id": record_id, "state": "imported", "result": result, "receipt": action_receipt, "execution_allowed": False, "automatic_execution": False, "claim": False}

    def _action_receipt(self, action_id: str, action: str, operator_id: str, record_id: str, state: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        unsigned = {"schema_version": RECEIPT_SCHEMA, "action_id": str(action_id), "action": str(action), "operator_id": str(operator_id), "record_id": str(record_id), "state": str(state), "bundle_digest": str(payload.get("bundle_digest", "")), "audit_digest": str(payload.get("audit_digest", "")), "execution_allowed": False, "automatic_import": False, "claim": False, "created_at": int(time.time())}
        return {**unsigned, "signature": _sign(unsigned, self.signing_key)}

    def status(self, record_id: str) -> Mapping[str, Any]:
        latest = self._latest(record_id)
        if latest is None:
            return {"schema_version": SCHEMA, "record_id": record_id, "state": "not_found", "available": False}
        receipt = latest[1].get("receipt") if isinstance(latest[1].get("receipt"), Mapping) else {}
        return {"schema_version": SCHEMA, "record_id": record_id, "state": latest[0], "available": True, "execution_allowed": False, "automatic_execution": False, "automatic_import": False, "claim": False, "reason": latest[1].get("reason", ""), "last_action": {"schema_version": receipt.get("schema_version", ""), "action_id": receipt.get("action_id", ""), "action": receipt.get("action", ""), "state": receipt.get("state", ""), "operator_id": receipt.get("operator_id", "")}}


def verify_ingestion_receipt(receipt: Mapping[str, Any], *, signing_key: bytes, record_id: str, bundle_digest: str, audit_digest: str) -> Mapping[str, Any]:
    if not isinstance(receipt, Mapping) or receipt.get("schema_version") != RECEIPT_SCHEMA:
        return {"status": "blocked", "reason": "receipt_schema_invalid", "claim": False}
    unsigned = {key: value for key, value in receipt.items() if key != "signature"}
    if not hmac.compare_digest(str(receipt.get("signature", "")), _sign(unsigned, signing_key)):
        return {"status": "blocked", "reason": "receipt_signature_invalid", "claim": False}
    if receipt.get("record_id") != record_id or receipt.get("bundle_digest") != bundle_digest or receipt.get("audit_digest") != audit_digest:
        return {"status": "blocked", "reason": "receipt_identity_mismatch", "claim": False}
    if receipt.get("execution_allowed") is not False or receipt.get("automatic_import") is not False or receipt.get("claim") is not False:
        return {"status": "blocked", "reason": "receipt_claim_escalation", "claim": False}
    if receipt.get("action") not in {"preflight", "approve", "import"} or receipt.get("state") not in {"awaiting_approval", "approved", "imported"}:
        return {"status": "blocked", "reason": "receipt_action_state_invalid", "claim": False}
    return {"status": "passed", "action_id": str(receipt.get("action_id", "")), "action": str(receipt.get("action")), "state": str(receipt.get("state")), "claim": False, "execution_claim": False, "comparative_claim": False}


def verify_ingestion_receipt_audit(receipts: Any, *, signing_key: bytes, record_id: str, bundle_digest: str, audit_digest: str) -> Mapping[str, Any]:
    if not isinstance(receipts, (list, tuple)) or not receipts:
        return {"status": "not_run", "reason": "receipts_missing", "claim": False, "execution_claim": False, "comparative_claim": False}
    verified = []
    seen = set()
    order = {"preflight": 0, "approve": 1, "import": 2}
    previous = -1
    for receipt in receipts:
        result = verify_ingestion_receipt(receipt, signing_key=signing_key, record_id=record_id, bundle_digest=bundle_digest, audit_digest=audit_digest)
        if result.get("status") != "passed":
            return {"status": "blocked", "reason": str(result.get("reason", "receipt_verification_failed")), "claim": False, "execution_claim": False, "comparative_claim": False}
        action_id = result["action_id"]
        if not action_id or action_id in seen:
            return {"status": "blocked", "reason": "receipt_duplicate_action_id", "claim": False, "execution_claim": False, "comparative_claim": False}
        if order[result["action"]] < previous:
            return {"status": "blocked", "reason": "receipt_order_invalid", "claim": False, "execution_claim": False, "comparative_claim": False}
        seen.add(action_id)
        previous = order[result["action"]]
        verified.append(result)
    return {"status": "passed", "record_id": record_id, "receipt_count": len(verified), "actions": verified, "claim": False, "execution_claim": False, "comparative_claim": False, "claim_boundary": "lifecycle_audit_only"}


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


__all__ = ["SCHEMA", "RECEIPT_SCHEMA", "STATES", "LifecycleAuditIngestionError", "LifecycleAuditIngestionAdapter", "verify_ingestion_receipt", "verify_ingestion_receipt_audit", "build_healthserver_wiring"]
