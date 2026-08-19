"""Create and verify signed offline artifact-set verification results.

Patterns are adapted from NOESIS signed evidence receipts, report bundles, and
operator artifact inventories. Results attest only to offline verification;
they never attest to execution, provider quality, or comparative superiority.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Mapping

SCHEMA = "noesis.signed-operator-artifact-verification.v1"


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def sign_verification_result(result: Mapping[str, Any], inventory_digest: str, root_digest: str, key: str) -> dict[str, Any]:
    if not isinstance(key, str) or len(key.encode("utf-8")) < 16:
        raise ValueError("verification_signing_key_too_short")
    unsigned = {
        "schema_version": SCHEMA,
        "verification_status": str(result.get("status", "blocked")),
        "comparative_ready": bool(result.get("comparative_ready", False)),
        "inventory_digest": str(inventory_digest),
        "root_digest": str(root_digest),
        "checks": dict(result.get("checks", {})) if isinstance(result.get("checks"), Mapping) else {},
        "automatic_execution": False,
        "external_execution_claim": False,
        "claim_boundary": "offline_artifact_verification_only",
    }
    return {**unsigned, "result_digest": _digest(unsigned), "signature": hmac.new(key.encode("utf-8"), _canonical(unsigned), hashlib.sha256).hexdigest()}


def verify_signed_verification_result(value: Mapping[str, Any], key: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or value.get("schema_version") != SCHEMA:
        return {"status": "blocked", "reason": "verification_result_schema_invalid"}
    if not isinstance(key, str) or len(key.encode("utf-8")) < 16:
        return {"status": "blocked", "reason": "verification_signing_key_too_short"}
    unsigned = {name: value[name] for name in value if name not in {"result_digest", "signature"}}
    if value.get("result_digest") != _digest(unsigned):
        return {"status": "blocked", "reason": "verification_result_digest_mismatch"}
    expected = hmac.new(key.encode("utf-8"), _canonical(unsigned), hashlib.sha256).hexdigest()
    if not isinstance(value.get("signature"), str) or not hmac.compare_digest(value["signature"], expected):
        return {"status": "blocked", "reason": "verification_result_signature_invalid"}
    if value.get("automatic_execution") is not False or value.get("external_execution_claim") is not False or value.get("claim_boundary") != "offline_artifact_verification_only":
        return {"status": "blocked", "reason": "verification_result_claim_boundary_invalid"}
    return {"status": "passed", "verification_status": str(value.get("verification_status", "blocked")), "result_digest": str(value["result_digest"])}
