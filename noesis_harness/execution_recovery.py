"""Authenticated rollback/recovery binding for child execution evidence.

This module verifies evidence and review state but never silently applies a patch.
A concrete rollback handler must be injected and must report whether the mutation
actually happened.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .execution_assurance import ExecutionReceiptStore, ExecutionRecoveryStore
from .workspaces import PatchReviewStore, WorkspaceError

RECOVERY_ACTION_SCHEMA = "noesis.execution-recovery-action.v1"


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

    def __post_init__(self) -> None:
        if self.schema_version != RECOVERY_ACTION_SCHEMA:
            raise ExecutionRecoveryError("unsupported_recovery_action_schema")
        for value, field in ((self.action_id, "action_id"), (self.run_id, "run_id"), (self.receipt_id, "receipt_id"), (self.proposal_id, "proposal_id"), (self.workspace_id, "workspace_id"), (self.current_base_snapshot_id, "current_base_snapshot_id"), (self.operator_id, "operator_id"), (self.session_id, "session_id")):
            if not value:
                raise ExecutionRecoveryError(field + "_required")
        if self.operation not in {"rollback", "recover"}:
            raise ExecutionRecoveryError("unsupported_recovery_operation")
        if not self.scope:
            raise ExecutionRecoveryError("recovery_scope_required")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ExecutionRecoveryAction":
        if not isinstance(value, Mapping):
            raise ExecutionRecoveryError("recovery_action_mapping_required")
        return cls(*(str(value.get(key, "")) for key in ("action_id", "operation", "run_id", "receipt_id", "proposal_id", "workspace_id", "current_base_snapshot_id", "operator_id", "session_id", "scope")), str(value.get("schema_version", RECOVERY_ACTION_SCHEMA)))

    def to_mapping(self) -> dict[str, str]:
        return {"schema_version": self.schema_version, "action_id": self.action_id, "operation": self.operation, "run_id": self.run_id, "receipt_id": self.receipt_id, "proposal_id": self.proposal_id, "workspace_id": self.workspace_id, "current_base_snapshot_id": self.current_base_snapshot_id, "operator_id": self.operator_id, "session_id": self.session_id, "scope": self.scope}


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

    def handle(self, action: ExecutionRecoveryAction, context: Mapping[str, Any]) -> Mapping[str, Any]:
        self._authorize(context, action)
        existing = self._existing(action.action_id)
        if existing is not None:
            return {"status": "replayed", "result": existing}
        receipt = self.receipt_store.get(action.receipt_id)
        if receipt is None or receipt.outcome not in {"committed", "failed", "timed_out"}:
            raise ExecutionRecoveryError("execution_receipt_not_recoverable")
        run = self.recovery_store.get(action.run_id)
        if run.get("receipt_id") != action.receipt_id:
            raise ExecutionRecoveryError("recovery_receipt_mismatch")
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
        payload = {"schema_version": RECOVERY_ACTION_SCHEMA, "action_id": action.action_id, "operation": action.operation, "run_id": action.run_id, "receipt_id": receipt.receipt_id, "proposal_id": proposal.proposal_id, "operator_id": action.operator_id, "status": operation_status, "rollback_performed": action.operation == "rollback", "recovery_state": state}
        self.events.append("execution_recovery_completed", payload, event_id="execution-recovery:" + action.action_id)
        return payload


__all__ = ["RECOVERY_ACTION_SCHEMA", "ExecutionRecoveryAction", "ExecutionRecoveryError", "ExecutionRecoveryExecutor"]
      
