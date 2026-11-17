"""Durable operator-run artifact ingestion lifecycle; never executes providers."""
from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import time
import uuid
from contextlib import closing
from pathlib import Path
from typing import Any, Mapping, Sequence

from scripts.build_operator_case_bundle import digest
from scripts.validate_operator_import import validate_import

SCHEMA = "noesis.operator-ingestion.v1"
STATES = frozenset({"preflight", "awaiting_approval", "approved", "imported", "blocked", "rejected"})


def _signature(payload: Mapping[str, Any], key: str) -> str:
    if not key or len(key) < 16:
        raise ValueError("ingestion signing key must be at least 16 characters")
    body = (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return "hmac-sha256:" + hmac.new(key.encode(), body, hashlib.sha256).hexdigest()


class OperatorIngestionLedger:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("CREATE TABLE IF NOT EXISTS ingestion_events (sequence INTEGER PRIMARY KEY AUTOINCREMENT, record_id TEXT NOT NULL, state TEXT NOT NULL, payload TEXT NOT NULL, created_at REAL NOT NULL)")
            db.commit()

    def _append(self, record_id: str, state: str, payload: Mapping[str, Any]) -> None:
        if state not in STATES:
            raise ValueError("invalid_ingestion_state")
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("INSERT INTO ingestion_events(record_id,state,payload,created_at) VALUES(?,?,?,?)", (record_id, state, json.dumps(dict(payload), ensure_ascii=False, sort_keys=True), time.time()))
            db.commit()

    def _latest(self, record_id: str) -> tuple[str, dict[str, Any]] | None:
        with closing(sqlite3.connect(self.path)) as db:
            row = db.execute("SELECT state,payload FROM ingestion_events WHERE record_id=? ORDER BY sequence DESC LIMIT 1", (record_id,)).fetchone()
        return (str(row[0]), json.loads(row[1])) if row else None

    def preflight(self, bundle: Mapping[str, Any], manifest: Mapping[str, Any]) -> dict[str, Any]:
        record_id = "ing-" + uuid.uuid4().hex
        bundle_digest = digest(bundle)
        state = "awaiting_approval" if bundle.get("status") != "blocked" and bundle.get("execution_allowed") is False else "blocked"
        payload = {"schema_version": SCHEMA, "record_id": record_id, "bundle_digest": bundle_digest, "manifest_digest": bundle.get("manifest_digest"), "execution_allowed": False, "automatic_execution": False, "external_execution_claim": False, "reason": "awaiting_explicit_operator_approval" if state == "awaiting_approval" else "bundle_preflight_blocked"}
        self._append(record_id, state, payload)
        return {**payload, "state": state}

    def approve(self, record_id: str, key: str, *, operator_id: str, ttl_seconds: float = 300.0, now: float | None = None) -> dict[str, Any]:
        latest = self._latest(record_id)
        if latest is None or latest[0] != "awaiting_approval":
            raise ValueError("approval_not_allowed")
        if ttl_seconds <= 0 or ttl_seconds > 3600:
            raise ValueError("approval_ttl_invalid")
        issued = float(time.time() if now is None else now)
        payload = {"schema_version": SCHEMA, "record_id": record_id, "operator_id": str(operator_id), "issued_at": issued, "expires_at": issued + ttl_seconds, "bundle_digest": latest[1].get("bundle_digest"), "manifest_digest": latest[1].get("manifest_digest"), "execution_allowed": False, "automatic_execution": False}
        receipt = {**payload, "signature": _signature(payload, key)}
        self._append(record_id, "approved", {**latest[1], "approval": receipt, "reason": "explicit_operator_approval_recorded"})
        return receipt

    def import_result(self, record_id: str, approval: Mapping[str, Any], key: str, bundle: Mapping[str, Any], manifest: Mapping[str, Any], evidence: Sequence[Mapping[str, Any]], cases: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        latest = self._latest(record_id)
        if latest is None or latest[0] != "approved":
            raise ValueError("import_requires_approved_record")
        payload = {name: approval.get(name) for name in ("schema_version", "record_id", "operator_id", "issued_at", "expires_at", "bundle_digest", "manifest_digest", "execution_allowed", "automatic_execution")}
        if approval.get("signature") != _signature(payload, key):
            self._append(record_id, "rejected", {**latest[1], "reason": "approval_signature_invalid"})
            raise ValueError("approval_signature_invalid")
        if float(approval.get("expires_at", 0)) <= time.time() or approval.get("record_id") != record_id or approval.get("bundle_digest") != latest[1].get("bundle_digest") or approval.get("manifest_digest") != latest[1].get("manifest_digest"):
            self._append(record_id, "rejected", {**latest[1], "reason": "approval_stale_or_identity_mismatch"})
            raise ValueError("approval_stale_or_identity_mismatch")
        result = validate_import(bundle, manifest, evidence, cases, key)
        state = "imported" if result["status"] in {"accepted", "accepted_not_run"} else "blocked"
        self._append(record_id, state, {**latest[1], "result": result, "external_execution_claim": False, "score_claim": False})
        return {"schema_version": SCHEMA, "record_id": record_id, "state": state, "result": result, "external_execution_claim": False, "score_claim": False}

    def status(self, record_id: str) -> dict[str, Any]:
        latest = self._latest(record_id)
        if latest is None:
            return {"schema_version": SCHEMA, "record_id": record_id, "state": "not_found", "available": False}
        state, payload = latest
        return {"schema_version": SCHEMA, "record_id": record_id, "state": state, "available": True, "execution_allowed": False, "automatic_execution": False, "external_execution_claim": False, "score_claim": False, "reason": payload.get("reason", ""), "result_status": payload.get("result", {}).get("status") if isinstance(payload.get("result"), Mapping) else None}
