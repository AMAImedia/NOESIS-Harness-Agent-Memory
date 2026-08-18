"""Prepare or execute a pinned external lane with explicit signed approval."""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import tempfile
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
    """Atomically record an approval ID; a previously consumed ID is rejected."""
    path = Path(store_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        used = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    except (OSError, ValueError):
        return False, "approval_store_invalid"
    if not isinstance(used, list):
        return False, "approval_store_invalid"
    approval_id = str(receipt.get("approval_id", ""))
    if not approval_id:
        return False, "approval_id_missing"
    if approval_id in used:
        return False, "approval_replay"
    used.append(approval_id)
    data = json.dumps(used, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    try:
        fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent), text=True)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except OSError:
        try:
            os.unlink(temp_name)
        except (OSError, UnboundLocalError):
            pass
        return False, "approval_store_write_failed"
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
