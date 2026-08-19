"""Sign and verify claim-conservative release-readiness receipts."""
from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Mapping

SCHEMA = "noesis.signed-release-readiness-receipt.v1"


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def sign_readiness_receipt(snapshot: Mapping[str, Any], gate_artifact: Mapping[str, Any], test_count: int, python_version: str, key: str) -> dict[str, Any]:
    if not isinstance(key, str) or len(key.encode("utf-8")) < 16:
        raise ValueError("readiness_signing_key_too_short")
    if test_count < 0:
        raise ValueError("readiness_test_count_invalid")
    unsigned = {
        "schema_version": SCHEMA,
        "readiness_status": str(snapshot.get("overall_status", "blocked")),
        "snapshot_digest": str(snapshot.get("snapshot_digest", "")),
        "gate_artifact_digest": str(gate_artifact.get("artifact_digest", "")),
        "gate_status": str(gate_artifact.get("status", "blocked")),
        "validated_test_count": int(test_count),
        "python_version": str(python_version),
        "native_host_status": str(snapshot.get("native_host_status", "not_run")),
        "external_lanes_status": str(snapshot.get("external_lanes_status", "not_run")),
        "automatic_execution": False,
        "external_execution_claim": False,
        "claim_boundary": "signed_release_readiness_summary_only",
    }
    return {**unsigned, "receipt_digest": _digest(unsigned), "signature": hmac.new(key.encode("utf-8"), _canonical(unsigned), hashlib.sha256).hexdigest()}


def verify_readiness_receipt(receipt: Mapping[str, Any], snapshot: Mapping[str, Any], gate_artifact: Mapping[str, Any], test_count: int, key: str) -> dict[str, Any]:
    if not isinstance(receipt, Mapping) or receipt.get("schema_version") != SCHEMA:
        return {"status": "blocked", "reason": "readiness_receipt_schema_invalid"}
    if not isinstance(key, str) or len(key.encode("utf-8")) < 16:
        return {"status": "blocked", "reason": "readiness_signing_key_too_short"}
    unsigned = {name: receipt[name] for name in receipt if name not in {"receipt_digest", "signature"}}
    if receipt.get("receipt_digest") != _digest(unsigned):
        return {"status": "blocked", "reason": "readiness_receipt_digest_mismatch"}
    expected = hmac.new(key.encode("utf-8"), _canonical(unsigned), hashlib.sha256).hexdigest()
    if not isinstance(receipt.get("signature"), str) or not hmac.compare_digest(receipt["signature"], expected):
        return {"status": "blocked", "reason": "readiness_receipt_signature_invalid"}
    if receipt.get("automatic_execution") is not False or receipt.get("external_execution_claim") is not False or receipt.get("claim_boundary") != "signed_release_readiness_summary_only":
        return {"status": "blocked", "reason": "readiness_receipt_claim_boundary_invalid"}
    if receipt.get("snapshot_digest") != snapshot.get("snapshot_digest"):
        return {"status": "blocked", "reason": "readiness_receipt_snapshot_drift"}
    if receipt.get("gate_artifact_digest") != gate_artifact.get("artifact_digest"):
        return {"status": "blocked", "reason": "readiness_receipt_gate_artifact_drift"}
    if int(receipt.get("validated_test_count", -1)) != int(test_count):
        return {"status": "blocked", "reason": "readiness_receipt_test_count_drift"}
    if receipt.get("readiness_status") != snapshot.get("overall_status") or receipt.get("gate_status") != gate_artifact.get("status"):
        return {"status": "blocked", "reason": "readiness_receipt_status_drift"}
    return {"status": "passed", "receipt_digest": str(receipt["receipt_digest"]), "readiness_status": str(receipt.get("readiness_status"))}
