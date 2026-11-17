"""Capability-scoped multi-agent delegation with isolated review-only artifacts.

Patterns are borrowed from NOESIS parallel_agent, workspace manifests, lease
coordination, and signed evidence receipts. Callbacks remain injected and are
never treated as a sandbox for executable tools or model-generated code.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from .parallel_agent import AgentLane, AgentLaneContext, AgentLaneResult, SafeParallelExecutor, SAFE_CAPABILITIES, APPROVAL_REQUIRED_CAPABILITIES

SCHEMA = "noesis.delegation-receipt.v1"


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DelegationRequest:
    delegation_id: str
    session_id: str
    task_id: str
    agent_id: str
    capabilities: tuple[str, ...] = ("read", "provenance")
    approval_granted: bool = False

    def __post_init__(self) -> None:
        for value, field in ((self.delegation_id, "delegation_id"), (self.session_id, "session_id"), (self.task_id, "task_id"), (self.agent_id, "agent_id")):
            if not isinstance(value, str) or not value:
                raise ValueError(field + "_required")
        if len(set(self.capabilities)) != len(self.capabilities):
            raise ValueError("duplicate_capabilities")


@dataclass(frozen=True)
class DelegationReceipt:
    delegation_id: str
    session_id: str
    task_id: str
    agent_id: str
    workspace: str
    capabilities: tuple[str, ...]
    status: str
    artifact_digest: str
    output_digest: str
    signed_receipt: str
    schema_version: str = SCHEMA

    def payload(self) -> dict[str, Any]:
        return {"schema_version": self.schema_version, "delegation_id": self.delegation_id, "session_id": self.session_id, "task_id": self.task_id, "agent_id": self.agent_id, "workspace": self.workspace, "capabilities": list(self.capabilities), "status": self.status, "artifact_digest": self.artifact_digest, "output_digest": self.output_digest}


class DelegationError(ValueError):
    """Raised when delegation violates capability or isolation policy."""


class DelegationCoordinator:
    """Run bounded delegated callbacks and persist review-only signed receipts."""

    def __init__(self, workspace_root: str, signing_key: bytes, *, max_concurrency: int = 2):
        if not isinstance(signing_key, bytes) or len(signing_key) < 16:
            raise ValueError("delegation_signing_key_too_short")
        self.executor = SafeParallelExecutor(workspace_root, max_concurrency=max_concurrency)
        self.root = Path(workspace_root).expanduser().resolve()
        self.key = signing_key

    @staticmethod
    def _artifact_digest(path: Path) -> str:
        entries = []
        for item in sorted(path.rglob("*")):
            if not item.is_file() or item.name in {".noesis-workspace", "DELEGATION_RECEIPT.json"}:
                continue
            relative = item.relative_to(path).as_posix()
            entries.append({"path": relative, "sha256": hashlib.sha256(item.read_bytes()).hexdigest(), "size": item.stat().st_size})
        return _digest(entries)

    def _sign(self, payload: Mapping[str, Any]) -> str:
        return hmac.new(self.key, _canonical(payload).encode("utf-8"), hashlib.sha256).hexdigest()

    def verify(self, receipt: DelegationReceipt) -> bool:
        return hmac.compare_digest(self._sign(receipt.payload()), receipt.signed_receipt)

    def delegate(self, request: DelegationRequest, callback: Callable[[AgentLaneContext], object], *, approval: bool = False, lease_store: Optional[object] = None, action_store: Optional[object] = None, cancellation: Optional[object] = None, max_duration_seconds: Optional[float] = None) -> tuple[DelegationReceipt, AgentLaneResult]:
        if not callable(callback):
            raise DelegationError("callback_required")
        caps = frozenset(request.capabilities)
        unknown = caps - SAFE_CAPABILITIES
        if unknown:
            raise DelegationError("capability_denied:" + ",".join(sorted(unknown)))
        if caps & APPROVAL_REQUIRED_CAPABILITIES and not (approval and request.approval_granted):
            raise DelegationError("capability_approval_required")
        lane = AgentLane(request.agent_id, request.task_id, request.delegation_id, tuple(sorted(caps)), bool(bool(caps & APPROVAL_REQUIRED_CAPABILITIES)), request.approval_granted)
        results = self.executor.execute([lane], callback, session_id=request.session_id, approval=approval, lease_store=lease_store, action_store=action_store, cancellation=cancellation, max_duration_seconds=max_duration_seconds)
        result = results[0]
        workspace = str(self.executor.workspace_root / request.delegation_id)
        artifact_digest = self._artifact_digest(Path(workspace))
        payload = {"schema_version": SCHEMA, "delegation_id": request.delegation_id, "session_id": request.session_id, "task_id": request.task_id, "agent_id": request.agent_id, "workspace": workspace, "capabilities": sorted(caps), "status": result.status, "artifact_digest": artifact_digest, "output_digest": _digest(result.output)}
        receipt = DelegationReceipt(request.delegation_id, request.session_id, request.task_id, request.agent_id, workspace, tuple(sorted(caps)), result.status, artifact_digest, _digest(result.output), self._sign(payload))
        receipt_path = Path(workspace) / "DELEGATION_RECEIPT.json"
        receipt_path.write_text(_canonical({"payload": payload, "signature": receipt.signed_receipt}) + "\n", encoding="utf-8")
        return receipt, result


__all__ = ["SCHEMA", "DelegationRequest", "DelegationReceipt", "DelegationError", "DelegationCoordinator"]
