"""Build and verify a signed NOESIS evidence-chain summary.

Patterns are adapted from artifact inventories, signed external aggregates, and
signed offline verification results. The summary is an integrity receipt only;
it never claims execution or comparative superiority.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Mapping

SCHEMA = "noesis.signed-evidence-chain-summary.v1"


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build_chain_summary(inventory: Mapping[str, Any], aggregate: Mapping[str, Any], verification: Mapping[str, Any], key: str) -> dict[str, Any]:
    if not isinstance(key, str) or len(key.encode("utf-8")) < 16:
        raise ValueError("chain_summary_signing_key_too_short")
    inventory_digest = str(inventory.get("inventory_digest", ""))
    aggregate_digest = str(aggregate.get("aggregate_digest", ""))
    verification_digest = str(verification.get("result_digest", ""))
    if not inventory_digest or not aggregate_digest or not verification_digest:
        raise ValueError("chain_summary_component_digest_missing")
    unsigned = {
        "schema_version": SCHEMA,
        "inventory_digest": inventory_digest,
        "aggregate_digest": aggregate_digest,
        "verification_result_digest": verification_digest,
        "status": str(verification.get("verification_status", "blocked")),
        "comparative_ready": bool(aggregate.get("comparative_ready", False)),
        "automatic_execution": False,
        "external_execution_claim": False,
        "claim_boundary": "offline_evidence_chain_integrity_only",
    }
    digest = hashlib.sha256(_canonical(unsigned)).hexdigest()
    return {**unsigned, "chain_digest": digest, "signature": hmac.new(key.encode("utf-8"), _canonical(unsigned), hashlib.sha256).hexdigest()}


def verify_chain_summary(summary: Mapping[str, Any], inventory: Mapping[str, Any], aggregate: Mapping[str, Any], verification: Mapping[str, Any], key: str) -> dict[str, Any]:
    if not isinstance(summary, Mapping) or summary.get("schema_version") != SCHEMA:
        return {"status": "blocked", "reason": "chain_summary_schema_invalid"}
    if not isinstance(key, str) or len(key.encode("utf-8")) < 16:
        return {"status": "blocked", "reason": "chain_summary_signing_key_too_short"}
    unsigned = {name: summary[name] for name in summary if name not in {"chain_digest", "signature"}}
    expected = hashlib.sha256(_canonical(unsigned)).hexdigest()
    if summary.get("chain_digest") != expected:
        return {"status": "blocked", "reason": "chain_summary_digest_mismatch"}
    expected_signature = hmac.new(key.encode("utf-8"), _canonical(unsigned), hashlib.sha256).hexdigest()
    if not isinstance(summary.get("signature"), str) or not hmac.compare_digest(summary["signature"], expected_signature):
        return {"status": "blocked", "reason": "chain_summary_signature_invalid"}
    if summary.get("inventory_digest") != inventory.get("inventory_digest"):
        return {"status": "blocked", "reason": "chain_summary_inventory_drift"}
    if summary.get("aggregate_digest") != aggregate.get("aggregate_digest"):
        return {"status": "blocked", "reason": "chain_summary_aggregate_drift"}
    if summary.get("verification_result_digest") != verification.get("result_digest"):
        return {"status": "blocked", "reason": "chain_summary_verification_drift"}
    if summary.get("automatic_execution") is not False or summary.get("external_execution_claim") is not False or summary.get("claim_boundary") != "offline_evidence_chain_integrity_only":
        return {"status": "blocked", "reason": "chain_summary_claim_boundary_invalid"}
    return {"status": "passed", "chain_digest": str(summary["chain_digest"])}
