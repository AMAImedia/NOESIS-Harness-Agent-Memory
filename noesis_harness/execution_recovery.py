"""Authenticated rollback/recovery binding for child execution evidence.

This module verifies evidence and review state but never silently applies a patch.
A concrete rollback handler must be injected and must report whether the mutation
actually happened.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .execution_assurance import ExecutionReceiptStore, ExecutionRecoveryStore, create_receipt, request_fingerprint
from .workspaces import PatchReviewStore, WorkspaceError

RECOVERY_ACTION_SCHEMA = "noesis.execution-recovery-action.v1"


def _completion_event_digest(payload: Mapping[str, Any]) -> str:
    return request_fingerprint({str(key): value for key, value in payload.items() if key != "previous_event_digest"})


class ExecutionRecoveryError(ValueError):
    """Raised when recovery action evidence or authorization is invalid."""


@dataclass(frozen=True)
class ExecutionRecoveryAction:
    action_id: str
    operation: str
    run_id: str
    receipt_id: str
    proposal_id: str
    workspace_id: str
    current_base_snapshot_id: str
    operator_id: str
    session_id: str
    scope: str = "runtime:recovery"
    schema_version: str = RECOVERY_ACTION_SCHEMA
    artifact_diff_digest: str = ""
    chain_snapshot_id: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != RECOVERY_ACTION_SCHEMA:
            raise ExecutionRecoveryError("unsupported_recovery_action_schema")
        for value, field in ((self.action_id, "action_id"), (self.run_id, "run_id"), (self.proposal_id, "proposal_id"), (self.workspace_id, "workspace_id"), (self.current_base_snapshot_id, "current_base_snapshot_id"), (self.operator_id, "operator_id"), (self.session_id, "session_id")):
            if not value:
                raise ExecutionRecoveryError(field + "_required")
        if self.operation == "rollback" and not self.receipt_id:
            raise ExecutionRecoveryError("receipt_id_required")
        if self.operation not in {"rollback", "recover"}:
            raise ExecutionRecoveryError("unsupported_recovery_operation")
        if not self.scope:
            raise ExecutionRecoveryError("recovery_scope_required")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ExecutionRecoveryAction":
        if not isinstance(value, Mapping):
            raise ExecutionRecoveryError("recovery_action_mapping_required")
        return cls(action_id=str(value.get("action_id", "")), operation=str(value.get("operation", "")), run_id=str(value.get("run_id", "")), receipt_id=str(value.get("receipt_id", "")), proposal_id=str(value.get("proposal_id", "")), workspace_id=str(value.get("workspace_id", "")), current_base_snapshot_id=str(value.get("current_base_snapshot_id", "")), operator_id=str(value.get("operator_id", "")), session_id=str(value.get("session_id", "")), scope=str(value.get("scope", "runtime:recovery")), schema_version=str(value.get("schema_version", RECOVERY_ACTION_SCHEMA)), artifact_diff_digest=str(value.get("artifact_diff_digest", "")), chain_snapshot_id=str(value.get("chain_snapshot_id", "")))

    def to_mapping(self) -> dict[str, str]:
        return {"schema_version": self.schema_version, "action_id": self.action_id, "operation": self.operation, "run_id": self.run_id, "receipt_id": self.receipt_id, "proposal_id": self.proposal_id, "workspace_id": self.workspace_id, "current_base_snapshot_id": self.current_base_snapshot_id, "operator_id": self.operator_id, "session_id": self.session_id, "scope": self.scope, "artifact_diff_digest": self.artifact_diff_digest, "chain_snapshot_id": self.chain_snapshot_id}


class ExecutionRecoveryExecutor:
    """Verify evidence and perform only an explicit injected rollback/recovery."""
    def __init__(self, *, receipt_store: ExecutionReceiptStore, recovery_store: ExecutionRecoveryStore, patch_store: PatchReviewStore, event_path: str, rollback_handler: Callable[[ExecutionRecoveryAction], bool] | None = None):
        from .event_store import EventStore
        self.receipt_store = receipt_store
        self.recovery_store = recovery_store
        self.patch_store = patch_store
        self.events = EventStore(event_path)
        self.rollback_handler = rollback_handler

    def _existing(self, action_id: str) -> Mapping[str, Any] | None:
        for event in self.events.iter_events():
            payload = event.get("payload") or {}
            if event.get("type") == "execution_recovery_completed" and payload.get("action_id") == action_id:
                return dict(payload)
        return None

    @staticmethod
    def _authorize(context: Mapping[str, Any], action: ExecutionRecoveryAction) -> None:
        if not isinstance(context, Mapping) or not context.get("authenticated"):
            raise PermissionError("recovery_authentication_required")
        if str(context.get("operator_id", "")) != action.operator_id:
            raise PermissionError("recovery_operator_identity_mismatch")
        if str(context.get("session_id", "")) != action.session_id:
            raise PermissionError("recovery_operator_session_mismatch")
        scopes = {str(item) for item in context.get("scopes", ())}
        if action.scope not in scopes:
            raise PermissionError("recovery_scope_denied")

    def audit_completion_events(self) -> Mapping[str, Any]:
        """Verify the hash-linked completion event chain and referenced receipts."""
        last_digest = "genesis"
        seen_actions = set()
        event_ids = []
        receipt_ids = []
        for event in self.events.iter_events():
            if event.get("type") != "execution_recovery_completed":
                continue
            payload = event.get("payload")
            if not isinstance(payload, Mapping):
                raise ExecutionRecoveryError("recovery_completion_event_corrupt")
            action_id = str(payload.get("action_id", ""))
            if not action_id or action_id in seen_actions:
                raise ExecutionRecoveryError("recovery_completion_event_fork")
            if str(payload.get("previous_event_digest", "")) != last_digest:
                raise ExecutionRecoveryError("recovery_completion_event_chain_mismatch")
            completion_receipt_id = str(payload.get("completion_receipt_id", ""))
            if completion_receipt_id:
                receipt = self.receipt_store.get(completion_receipt_id)
                if receipt is None or receipt.outcome != "committed":
                    raise ExecutionRecoveryError("recovery_completion_receipt_invalid")
                receipt_ids.append(completion_receipt_id)
            seen_actions.add(action_id)
            event_id = str(event.get("event_id", ""))
            event_ids.append(event_id)
            last_digest = _completion_event_digest(payload)
        return {"status": "passed", "count": len(event_ids), "event_ids": tuple(event_ids), "completion_receipt_ids": tuple(receipt_ids), "chain_digest": last_digest}

    def handle(self, action: ExecutionRecoveryAction, context: Mapping[str, Any]) -> Mapping[str, Any]:
        self._authorize(context, action)
        existing = self._existing(action.action_id)
        action_digest = request_fingerprint(action.to_mapping())
        if existing is not None:
            if existing.get("action_digest") != action_digest:
                raise ExecutionRecoveryError("recovery_action_replay_conflict")
            completion_receipt_id = str(existing.get("completion_receipt_id", ""))
            if completion_receipt_id:
                completion_receipt = self.receipt_store.get(completion_receipt_id)
                if completion_receipt is None or completion_receipt.outcome != "committed":
                    raise ExecutionRecoveryError("recovery_completion_receipt_invalid")
            return {"status": "replayed", "result": existing}
        run = self.recovery_store.get(action.run_id)
        receipt = None
        proposal = None
        chain_snapshot = None
        if action.operation == "recover":
            if run.get("status") != "running":
                raise ExecutionRecoveryError("interrupted_run_required")
            if action.receipt_id and run.get("receipt_id") not in {None, "", action.receipt_id}:
                raise ExecutionRecoveryError("recovery_receipt_mismatch")
        else:
            if action.chain_snapshot_id:
                chain_snapshot = self.receipt_store.get_chain_snapshot(action.chain_snapshot_id)
                if action.receipt_id not in tuple(chain_snapshot.get("receipt_ids", ())):
                    raise ExecutionRecoveryError("recovery_chain_snapshot_mismatch")
            receipt = self.receipt_store.get(action.receipt_id)
            if receipt is None or receipt.outcome not in {"committed", "failed", "timed_out"}:
                raise ExecutionRecoveryError("execution_receipt_not_recoverable")
            if run.get("receipt_id") != action.receipt_id:
                raise ExecutionRecoveryError("recovery_receipt_mismatch")
            if action.artifact_diff_digest and receipt.artifact_diff_digest != action.artifact_diff_digest:
                raise ExecutionRecoveryError("recovery_artifact_diff_mismatch")
            proposal = self.patch_store.get(action.proposal_id)
            if proposal.workspace_id != action.workspace_id:
                raise ExecutionRecoveryError("recovery_workspace_mismatch")
            if proposal.status != "approved":
                raise ExecutionRecoveryError("approved_patch_required")
            if proposal.base_snapshot_id != action.current_base_snapshot_id:
                raise ExecutionRecoveryError("recovery_base_stale")
        if self.rollback_handler is None:
            raise ExecutionRecoveryError("rollback_handler_required")
        applied = bool(self.rollback_handler(action))
        if not applied:
            raise ExecutionRecoveryError("rollback_not_confirmed")
        if action.operation == "rollback":
            state = self.recovery_store.mark_rolled_back(action.run_id)
            operation_status = "rolled_back"
        else:
            state = self.recovery_store.mark_recovered(action.run_id)
            operation_status = "recovered"
        completion = create_receipt(request={"recovery_action": action.to_mapping(), "run_id": action.run_id, "operation_status": operation_status}, policy={"scope": action.scope, "operator_id": action.operator_id, "chain_snapshot_id": action.chain_snapshot_id}, workspace_before=str(state.get("workspace_before", "")), workspace_after=state.get("workspace_after"), outcome="committed", rollback_available=False, side_effects=("recovery:" + operation_status,), signing_key=self.receipt_store.signing_key, artifact_diff={"digest": action.artifact_diff_digest} if action.artifact_diff_digest else None)
        self.receipt_store.put(completion)
        prior_digest = "genesis"
        for event in self.events.iter_events():
            if event.get("type") == "execution_recovery_completed":
                prior_digest = _completion_event_digest(event.get("payload") or {})
        payload = {"schema_version": RECOVERY_ACTION_SCHEMA, "action_id": action.action_id, "action_digest": action_digest, "operation": action.operation, "run_id": action.run_id, "receipt_id": receipt.receipt_id if receipt is not None else "", "proposal_id": proposal.proposal_id if proposal is not None else "", "operator_id": action.operator_id, "status": operation_status, "rollback_performed": action.operation == "rollback", "artifact_diff_digest": action.artifact_diff_digest, "chain_snapshot_id": action.chain_snapshot_id, "chain_snapshot_digest": chain_snapshot.get("snapshot_digest", "") if chain_snapshot is not None else "", "completion_receipt_id": completion.receipt_id, "recovery_state": state, "previous_event_digest": prior_digest}
        self.events.append("execution_recovery_completed", payload, event_id="execution-recovery:" + action.action_id)
        return payload


__all__ = ["RECOVERY_ACTION_SCHEMA", "ExecutionRecoveryAction", "ExecutionRecoveryError", "ExecutionRecoveryExecutor", "_completion_event_digest"]
      
