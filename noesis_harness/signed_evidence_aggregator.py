"""Fail-closed aggregation of signed delegated and child-runtime evidence.

Patterns adapted from the project's execution receipts, comparative evidence
readiness, operator ingestion ledger, and signed mutation receipts. Aggregation
never executes providers or child processes and never upgrades not_run evidence.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "noesis.signed-evidence-aggregate.v1"


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(value), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def sign_evidence(receipt: Mapping[str, Any], signing_key: bytes) -> str:
    if not isinstance(signing_key, bytes) or len(signing_key) < 16:
        raise ValueError("signing_key_too_short")
    return hmac.new(signing_key, _canonical(receipt), hashlib.sha256).hexdigest()


def verify_evidence(receipt: Mapping[str, Any], signature: str, signing_key: bytes) -> bool:
    if not isinstance(signature, str) or not isinstance(signing_key, bytes) or len(signing_key) < 16:
        return False
    return hmac.compare_digest(sign_evidence(receipt, signing_key), signature)


@dataclass(frozen=True)
class AggregateEvidence:
    status: str
    reason: str
    evidence_count: int
    lanes: tuple[str, ...]
    aggregate_digest: str
    comparative_claim: bool = False
    execution_claim: bool = False

    def to_mapping(self) -> dict[str, Any]:
        return {"schema_version": SCHEMA_VERSION, "status": self.status, "reason": self.reason, "evidence_count": self.evidence_count, "lanes": list(self.lanes), "aggregate_digest": self.aggregate_digest, "comparative_claim": self.comparative_claim, "execution_claim": self.execution_claim}


class SignedEvidenceAggregationError(ValueError):
    """Raised when input evidence cannot be safely aggregated."""


class SignedEvidenceAggregator:
    """Verify and aggregate already-produced receipts without executing them."""

    def __init__(self, signing_key: bytes, *, required_lanes: Sequence[str] = ("delegated", "child_runtime")):
        if not isinstance(signing_key, bytes) or len(signing_key) < 16:
            raise ValueError("signing_key_too_short")
        self.signing_key = signing_key
        self.required_lanes = tuple(str(item) for item in required_lanes)

    def aggregate(self, records: Sequence[Mapping[str, Any]]) -> AggregateEvidence:
        if not isinstance(records, Sequence) or isinstance(records, (str, bytes)) or not records:
            return AggregateEvidence("not_run", "evidence_records_required", 0, (), _digest({"records": []}))
        seen: set[str] = set()
        lanes: set[str] = set()
        normalized: list[Mapping[str, Any]] = []
        for record in records:
            if not isinstance(record, Mapping):
                return AggregateEvidence("blocked", "evidence_record_must_be_object", len(normalized), tuple(sorted(lanes)), _digest({"records": normalized}))
            required = ("evidence_id", "lane", "session_id", "task_id", "request_digest", "status", "receipt", "signature")
            if any(not str(record.get(key, "")) for key in required):
                return AggregateEvidence("blocked", "evidence_identity_incomplete", len(normalized), tuple(sorted(lanes)), _digest({"records": normalized}))
            evidence_id = str(record["evidence_id"])
            if evidence_id in seen:
                return AggregateEvidence("blocked", "duplicate_evidence_id", len(normalized), tuple(sorted(lanes)), _digest({"records": normalized}))
            receipt = record["receipt"]
            if not isinstance(receipt, Mapping) or not verify_evidence(receipt, str(record["signature"]), self.signing_key):
                return AggregateEvidence("blocked", "receipt_signature_invalid", len(normalized), tuple(sorted(lanes)), _digest({"records": normalized}))
            if str(receipt.get("session_id", "")) != str(record["session_id"]) or str(receipt.get("task_id", "")) != str(record["task_id"]) or str(receipt.get("request_digest", "")) != str(record["request_digest"]):
                return AggregateEvidence("blocked", "receipt_identity_mismatch", len(normalized), tuple(sorted(lanes)), _digest({"records": normalized}))
            if str(record["status"]) != "passed" or str(receipt.get("status", "")) != "passed":
                return AggregateEvidence("blocked", "non_passed_evidence_cannot_aggregate", len(normalized), tuple(sorted(lanes)), _digest({"records": normalized}))
            seen.add(evidence_id)
            lanes.add(str(record["lane"]))
            normalized.append({"evidence_id": evidence_id, "lane": str(record["lane"]), "session_id": str(record["session_id"]), "task_id": str(record["task_id"]), "request_digest": str(record["request_digest"]), "status": "passed", "receipt": dict(receipt), "signature": str(record["signature"])})
        missing = sorted(set(self.required_lanes) - lanes)
        aggregate_digest = _digest({"records": normalized, "required_lanes": self.required_lanes})
        if missing:
            return AggregateEvidence("not_run", "missing_required_lanes:" + ",".join(missing), len(normalized), tuple(sorted(lanes)), aggregate_digest)
        return AggregateEvidence("passed", "all_required_signed_evidence_verified", len(normalized), tuple(sorted(lanes)), aggregate_digest, comparative_claim=False, execution_claim=True)


__all__ = ["SCHEMA_VERSION", "AggregateEvidence", "SignedEvidenceAggregationError", "SignedEvidenceAggregator", "sign_evidence", "verify_evidence"]
