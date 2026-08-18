"""Prepare or execute a pinned external lane with explicit signed approval."""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Mapping

from scripts.ingest_runner_result import canonical, signature
from scripts.pinned_runner_adapter import RunnerConfigurationError, execute, validate

APPROVAL_SCHEMA = "noesis.external-approval.v1"


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


def consume_approval_receipt(receipt: Mapping[str, Any], store_path: str) -> tuple[bool, str]:
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
        db.execute("BEGIN IMMEDIATE")
        try:
            db.execute("INSERT INTO consumed_approvals(approval_id, consumed_at) VALUES(?, ?)", (approval_id, time.time()))
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
    args = parser.parse_args(argv)
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
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
            outcome = execute(spec, args.workspace, approval=True, timeout=args.timeout)
            report.update({"execution": "started", "status": outcome.status, "returncode": outcome.returncode, "stdout": outcome.stdout, "stderr": outcome.stderr, "timed_out": outcome.timed_out, "approval_id": receipt["approval_id"]})
    except (RunnerConfigurationError, PermissionError, OSError, ValueError, json.JSONDecodeError) as exc:
        report = {"schema_version": "noesis.external-lane-plan.v1", "execution": "denied", "status": "not_run", "reason": str(exc)}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "execution": report["execution"], "status": report.get("status", "not_run")}, ensure_ascii=False))
    return 0 if report["execution"] == "not_started" or report.get("status") == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())

__all__ = ["APPROVAL_SCHEMA", "consume_approval_receipt", "create_approval_receipt", "plan", "verify_approval_receipt"]
