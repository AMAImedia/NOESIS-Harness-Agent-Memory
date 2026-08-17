"""Tamper-evident execution receipts and recovery guarantees."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Optional

ASSURANCE_SCHEMA = "noesis.execution-assurance.v1"


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ExecutionReceipt:
    receipt_id: str
    schema_version: str
    request_digest: str
    policy_digest: str
    workspace_before: str
    workspace_after: Optional[str]
    outcome: str
    rollback_available: bool
    side_effects: tuple[str, ...]
    receipt_digest: str


class AssuranceError(ValueError):
    pass


def create_receipt(*, request: Mapping[str, Any], policy: Mapping[str, Any], workspace_before: str, workspace_after: Optional[str], outcome: str, rollback_available: bool, side_effects: tuple[str, ...] = ()) -> ExecutionReceipt:
    if outcome not in {"prepared", "committed", "rejected", "failed", "timed_out", "rolled_back"}:
        raise AssuranceError("invalid_outcome")
    if not workspace_before:
        raise AssuranceError("workspace_before_required")
    request_digest = _digest(request)
    policy_digest = _digest(policy)
    stable = {"request_digest": request_digest, "policy_digest": policy_digest, "workspace_before": workspace_before, "workspace_after": workspace_after, "outcome": outcome, "rollback_available": rollback_available, "side_effects": list(side_effects)}
    receipt_digest = _digest(stable)
    receipt_id = "receipt:" + receipt_digest[7:]
    return ExecutionReceipt(receipt_id, ASSURANCE_SCHEMA, request_digest, policy_digest, workspace_before, workspace_after, outcome, rollback_available, tuple(side_effects), receipt_digest)


def verify_receipt(receipt: ExecutionReceipt) -> bool:
    stable = {"request_digest": receipt.request_digest, "policy_digest": receipt.policy_digest, "workspace_before": receipt.workspace_before, "workspace_after": receipt.workspace_after, "outcome": receipt.outcome, "rollback_available": receipt.rollback_available, "side_effects": list(receipt.side_effects)}
    return receipt.schema_version == ASSURANCE_SCHEMA and receipt.receipt_id == "receipt:" + receipt.receipt_digest[7:] and receipt.receipt_digest == _digest(stable)


__all__ = ["ASSURANCE_SCHEMA", "AssuranceError", "ExecutionReceipt", "create_receipt", "verify_receipt"]
