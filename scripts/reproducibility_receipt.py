"""Build and verify reproducibility receipts for NOESIS evidence transfers.

The receipt records stable interpreter and contract fingerprints. Observation
 timestamps are deliberately excluded from the signed canonical payload so
repeated verification remains deterministic across hosts and reruns.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import platform
import sys
from typing import Any, Mapping

SCHEMA = "noesis.signed-reproducibility-receipt.v1"


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _fingerprint() -> dict[str, str]:
    return {
        "python_implementation": platform.python_implementation(),
        "python_version": "%d.%d.%d" % sys.version_info[:3],
        "platform_system": platform.system(),
        "platform_machine": platform.machine(),
    }


def build_reproducibility_receipt(inventory_digest: str, aggregate_digest: str, chain_digest: str, key: str, observed_at: str | None = None) -> dict[str, Any]:
    if not isinstance(key, str) or len(key.encode("utf-8")) < 16:
        raise ValueError("reproducibility_signing_key_too_short")
    unsigned = {
        "schema_version": SCHEMA,
        "inventory_digest": str(inventory_digest),
        "aggregate_digest": str(aggregate_digest),
        "chain_digest": str(chain_digest),
        "runtime_fingerprint": _fingerprint(),
        "contract_versions": {"inventory": "noesis.operator-artifact-inventory.v1", "aggregate": "noesis.signed-external-evidence-aggregate.v1", "chain": "noesis.signed-evidence-chain-summary.v1"},
        "timestamp_policy": "excluded_from_signed_payload",
        "automatic_execution": False,
        "external_execution_claim": False,
        "claim_boundary": "reproducibility_metadata_only",
    }
    result = {**unsigned, "receipt_digest": hashlib.sha256(_canonical(unsigned)).hexdigest(), "signature": hmac.new(key.encode("utf-8"), _canonical(unsigned), hashlib.sha256).hexdigest()}
    if observed_at is not None:
        result["observed_at"] = str(observed_at)
    return result


def verify_reproducibility_receipt(receipt: Mapping[str, Any], inventory_digest: str, aggregate_digest: str, chain_digest: str, key: str) -> dict[str, Any]:
    if not isinstance(receipt, Mapping) or receipt.get("schema_version") != SCHEMA:
        return {"status": "blocked", "reason": "reproducibility_schema_invalid"}
    unsigned = {name: receipt[name] for name in receipt if name not in {"receipt_digest", "signature", "observed_at"}}
    if receipt.get("receipt_digest") != hashlib.sha256(_canonical(unsigned)).hexdigest():
        return {"status": "blocked", "reason": "reproducibility_digest_mismatch"}
    if not isinstance(key, str) or len(key.encode("utf-8")) < 16:
        return {"status": "blocked", "reason": "reproducibility_signing_key_too_short"}
    expected = hmac.new(key.encode("utf-8"), _canonical(unsigned), hashlib.sha256).hexdigest()
    if not isinstance(receipt.get("signature"), str) or not hmac.compare_digest(receipt["signature"], expected):
        return {"status": "blocked", "reason": "reproducibility_signature_invalid"}
    if receipt.get("inventory_digest") != inventory_digest or receipt.get("aggregate_digest") != aggregate_digest or receipt.get("chain_digest") != chain_digest:
        return {"status": "blocked", "reason": "reproducibility_component_drift"}
    if receipt.get("timestamp_policy") != "excluded_from_signed_payload" or receipt.get("automatic_execution") is not False or receipt.get("external_execution_claim") is not False or receipt.get("claim_boundary") != "reproducibility_metadata_only":
        return {"status": "blocked", "reason": "reproducibility_claim_boundary_invalid"}
    return {"status": "passed", "receipt_digest": str(receipt["receipt_digest"]), "runtime_fingerprint": dict(receipt.get("runtime_fingerprint", {}))}
