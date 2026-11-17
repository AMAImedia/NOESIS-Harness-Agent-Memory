"""Prepare or execute a pinned external lane with explicit signed approval."""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Mapping

from scripts.ingest_runner_result import canonical, signature
from scripts.pinned_runner_adapter import RunnerConfigurationError, execute, validate

APPROVAL_SCHEMA = "noesis.external-approval.v1"
EXECUTION_STATES = frozenset({"consumed", "started", "completed", "abandoned"})


def _identity(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "system": report.get("system"),
        "revision": report.get("revision"),
        "protocol_fingerprint": report.get("protocol_fingerprint"),
        "task_manifest_sha256": report.get("task_manifest_sha256"),
        "workspace": report.get("workspace"),
        "command_sha256": report.get("command_sha256"),
    }


def _approval_id(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical(payload)).hexdigest()


def plan(spec: dict[str, Any], workspace: str) -> dict[str, Any]:
    argv, root, environment = validate(spec, workspace)
    command_digest = hashlib.sha256(json.dumps(argv, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {
        "schema_version": "noesis.external-lane-plan.v1",
        "execution": "not_started",
        "system": spec["system"],
        "revision": spec["revision"],
        "protocol_fingerprint": spec["protocol_fingerprint"],
        "task_manifest_sha256": spec["task_manifest_sha256"],
        "workspace": str(root),
        "command_sha256": command_digest,
        "argv_length": len(argv),
        "environment_keys": sorted(environment),
        "approval_required": True,
        "approval_schema": APPROVAL_SCHEMA,
        "reason": "dry_run_only",
    }


def create_approval_receipt(plan_report: Mapping[str, Any], key: str, *, now: float | None = None, ttl_seconds: float = 300.0, nonce: str | None = None) -> dict[str, Any]:
    if not key or len(key) < 16:
        raise ValueError("approval signing key must be at least 16 characters")
    if ttl_seconds <= 0 or ttl_seconds > 3600:
        raise ValueError("approval ttl must be between 0 and 3600 seconds")
    issued_at = float(time.time() if now is None else now)
    payload = {
        "schema_version": APPROVAL_SCHEMA,
        "issued_at": issued_at,
        "expires_at": issued_at + float(ttl_seconds),
        "nonce": str(nonce or os.urandom(16).hex()),
        "plan_identity": _identity(plan_report),
    }
    return {**payload, "approval_id": _approval_id(payload), "signature": signature(payload | {"approval_id": _approval_id(payload)}, key)}


def verify_approval_receipt(receipt: Mapping[str, Any], plan_report: Mapping[str, Any], key: str, *, now: float | None = None) -> tuple[bool, str]:
    if not isinstance(receipt, Mapping) or receipt.get("schema_version") != APPROVAL_SCHEMA:
        return False, "invalid_approval_schema"
    if not key or len(key) < 16:
        return False, "approval_key_invalid"
    unsigned = {name: value for name, value in receipt.items() if name != "signature"}
    expected_id = _approval_id({name: value for name, value in unsigned.items() if name != "approval_id"})
    if receipt.get("approval_id") != expected_id:
        return False, "approval_id_mismatch"
    supplied = receipt.get("signature")
    try:
        expected_signature = signature(unsigned, key)
    except (TypeError, ValueError, UnicodeError):
        return False, "approval_signature_invalid"
    if not isinstance(supplied, str) or not hmac.compare_digest(supplied, expected_signature):
        return False, "approval_signature_invalid"
    try:
        current = float(time.time() if now is None else now)
        if float(receipt["expires_at"]) <= current:
            return False, "approval_expired"
        if float(receipt["issued_at"]) > current + 30.0:
            return False, "approval_issued_in_future"
    except (KeyError, TypeError, ValueError, OverflowError):
        return False, "approval_time_invalid"
    if receipt.get("plan_identity") != _identity(plan_report):
        return False, "approval_plan_identity_mismatch"
    return True, "approved"


_CONSUME_LOCK = threading.Lock()


def _consume_approval_receipt(receipt: Mapping[str, Any], store_path: str) -> tuple[bool, str]:
    """Consume an approval exactly once using a transactional SQLite/WAL store."""
    path = Path(store_path)
    approval_id = str(receipt.get("approval_id", ""))
    if not approval_id:
        return False, "approval_id_missing"
    db: sqlite3.Connection | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(path, timeout=5.0, isolation_level=None)
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("CREATE TABLE IF NOT EXISTS consumed_approvals (approval_id TEXT PRIMARY KEY, consumed_at REAL NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS approval_execution_journal (approval_id TEXT PRIMARY KEY, state TEXT NOT NULL, updated_at REAL NOT NULL, detail TEXT NOT NULL)")
        db.execute("BEGIN IMMEDIATE")
        try:
            now = time.time()
            db.execute("INSERT INTO consumed_approvals(approval_id, consumed_at) VALUES(?, ?)", (approval_id, now))
            db.execute("INSERT INTO approval_execution_journal(approval_id, state, updated_at, detail) VALUES(?, 'consumed', ?, '')", (approval_id, now))
        except sqlite3.IntegrityError:
            db.execute("ROLLBACK")
            return False, "approval_replay"
        db.execute("COMMIT")
    except (OSError, sqlite3.DatabaseError):
        return False, "approval_store_invalid"
    finally:
        if db is not None:
            db.close()
    return True, "consumed"


def consume_approval_receipt(receipt: Mapping[str, Any], store_path: str) -> tuple[bool, str]:
    """Consume an approval exactly once, serializing local concurrent callers."""
    with _CONSUME_LOCK:
        return _consume_approval_receipt(receipt, store_path)


def record_execution_state(receipt_store: str, approval_id: str, state: str, detail: str = "") -> tuple[bool, str]:
    """Advance a consumed approval through a monotonic durable execution state machine."""
    if state not in EXECUTION_STATES:
        return False, "execution_state_invalid"
    transitions = {"consumed": {"started", "abandoned"}, "started": {"completed", "abandoned"}, "completed": set(), "abandoned": set()}
    db: sqlite3.Connection | None = None
    try:
        db = sqlite3.connect(Path(receipt_store), timeout=5.0, isolation_level=None)
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT state FROM approval_execution_journal WHERE approval_id=?", (approval_id,)).fetchone()
        if row is None:
            db.execute("ROLLBACK")
            return False, "execution_record_missing"
        current = str(row[0])
        if state != current and state not in transitions.get(current, set()):
            db.execute("ROLLBACK")
            return False, "execution_transition_invalid"
        db.execute("UPDATE approval_execution_journal SET state=?, updated_at=?, detail=? WHERE approval_id=?", (state, time.time(), str(detail)[:512], approval_id))
        db.execute("COMMIT")
        return True, "state_recorded"
    except (OSError, sqlite3.DatabaseError):
        return False, "approval_store_invalid"
    finally:
        if db is not None:
            db.close()


def recover_execution(receipt_store: str, approval_id: str) -> dict[str, str]:
    """Return a conservative recovery decision; an interrupted receipt is never auto-reused."""
    db: sqlite3.Connection | None = None
    try:
        db = sqlite3.connect(Path(receipt_store), timeout=5.0)
        row = db.execute("SELECT state FROM approval_execution_journal WHERE approval_id=?", (approval_id,)).fetchone()
    except (OSError, sqlite3.DatabaseError):
        return {"status": "blocked", "reason": "approval_store_invalid", "action": "operator_review"}
    finally:
        if db is not None:
            db.close()
    if row is None:
        return {"status": "not_found", "reason": "execution_record_missing", "action": "operator_review"}
    state = str(row[0])
    if state == "completed":
        return {"status": "completed", "reason": "execution_already_completed", "action": "no_replay"}
    if state == "abandoned":
        return {"status": "abandoned", "reason": "execution_abandoned", "action": "issue_new_approval"}
    return {"status": "interrupted", "reason": "execution_not_terminal", "action": "issue_new_approval"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Plan or explicitly execute a pinned NOESIS external lane")
    parser.add_argument("--spec", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--approve", action="store_true")
    parser.add_argument("--approval-receipt")
    parser.add_argument("--approval-key")
    parser.add_argument("--receipt-store")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--allowlist-file", help="model_api allowlist: one host per line; required for model_task lanes")
    args = parser.parse_args(argv)
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    allowlisted_hosts = None
    if spec.get("task_execution_class") == "model_task" and args.execute:
        if not args.allowlist_file:
            raise PermissionError("--allowlist-file is required for model_task lanes")
        allowlisted_hosts = [line.strip() for line in Path(args.allowlist_file).read_text(encoding="utf-8").splitlines() if line.strip() and not line.strip().startswith("#")]
    try:
        report = plan(spec, args.workspace)
        if args.execute:
            if not args.approve:
                raise PermissionError("--execute requires --approve")
            if not args.approval_receipt or not args.approval_key or not args.receipt_store:
                raise PermissionError("signed approval receipt, --approval-key and --receipt-store are required")
            receipt = json.loads(Path(args.approval_receipt).read_text(encoding="utf-8"))
            valid, reason = verify_approval_receipt(receipt, report, args.approval_key)
            if not valid:
                raise PermissionError(reason)
            if args.receipt_store:
                consumed, reason = consume_approval_receipt(receipt, args.receipt_store)
                if not consumed:
                    raise PermissionError(reason)
                started, reason = record_execution_state(args.receipt_store, receipt["approval_id"], "started", "approved runner started")
                if not started:
                    raise PermissionError(reason)
            try:
                outcome = execute(spec, args.workspace, approval=True, timeout=args.timeout, allowlisted_hosts=allowlisted_hosts)
                if allowlisted_hosts is not None:
                    report["allowlist"] = sorted(allowlisted_hosts)
                    report["jail"] = {"blocked_hosts": sorted(set(getattr(outcome, "jail_blocked_hosts", ()))), "allowed_count": getattr(outcome, "jail_allowed_count", 0)}
            except Exception:
                if args.receipt_store:
                    record_execution_state(args.receipt_store, receipt["approval_id"], "abandoned", "runner raised before terminal outcome")
                raise
            if args.receipt_store:
                terminal_state = "abandoned" if outcome.timed_out else "completed"
                terminal_detail = "runner timed out" if outcome.timed_out else "runner returned " + outcome.status
                recorded, reason = record_execution_state(args.receipt_store, receipt["approval_id"], terminal_state, terminal_detail)
                if not recorded:
                    raise PermissionError(reason)
            report.update({"execution": "started", "status": outcome.status, "returncode": outcome.returncode, "stdout": outcome.stdout, "stderr": outcome.stderr, "timed_out": outcome.timed_out, "approval_id": receipt["approval_id"], "journal_state": "abandoned" if outcome.timed_out else "completed"})
    except (RunnerConfigurationError, PermissionError, OSError, ValueError, json.JSONDecodeError) as exc:
        report = {"schema_version": "noesis.external-lane-plan.v1", "execution": "denied", "status": "not_run", "reason": str(exc)}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "execution": report["execution"], "status": report.get("status", "not_run")}, ensure_ascii=False))
    return 0 if report["execution"] == "not_started" or report.get("status") == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())

__all__ = ["APPROVAL_SCHEMA", "EXECUTION_STATES", "consume_approval_receipt", "create_approval_receipt", "plan", "record_execution_state", "recover_execution", "verify_approval_receipt"]
