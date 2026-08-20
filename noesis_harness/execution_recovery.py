"""Authenticated rollback/recovery binding for child execution evidence.

This module verifies evidence and review state but never silently applies a patch.
A concrete rollback handler must be injected and must report whether the mutation
actually happened.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import tempfile
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .execution_assurance import ExecutionReceiptStore, ExecutionRecoveryStore, create_receipt, request_fingerprint
from .workspaces import PatchReviewStore, WorkspaceError

RECOVERY_ACTION_SCHEMA = "noesis.execution-recovery-action.v1"


def _completion_event_digest(payload: Mapping[str, Any]) -> str:
    return request_fingerprint({str(key): value for key, value in payload.items() if key != "previous_event_digest"})


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


def _snapshot_signature(payload: Mapping[str, Any], key: bytes) -> str:
    return hmac.new(key, _canonical(payload), hashlib.sha256).hexdigest()


def _atomic_write_json(path: str, value: Mapping[str, Any]) -> None:
    parent = os.path.dirname(os.path.abspath(path)) or "."
    fd, temporary = tempfile.mkstemp(prefix=".recovery-chain-", suffix=".tmp", dir=parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


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

    def _completion_snapshot_path(self) -> str:
        return str(self.events.path) + ".snapshot.json"

    def persist_completion_event_snapshot(self) -> Mapping[str, Any]:
        """Atomically persist a signed projection snapshot of completion events."""
        audit = self.audit_completion_events()
        payload = {"schema_version": "noesis.recovery-event-chain-snapshot.v1", "event_path": str(self.events.path), "event_ids": list(audit["event_ids"]), "completion_receipt_ids": list(audit["completion_receipt_ids"]), "chain_digest": audit["chain_digest"], "count": audit["count"]}
        snapshot = {"payload": payload, "signature": _snapshot_signature(payload, self.receipt_store.signing_key)}
        _atomic_write_json(self._completion_snapshot_path(), snapshot)
        return snapshot

    def verify_completion_event_snapshot(self) -> Mapping[str, Any]:
        """Verify a signed snapshot against the current append-only event log."""
        path = self._completion_snapshot_path()
        try:
            with open(path, "r", encoding="utf-8") as handle:
                snapshot = json.load(handle)
            payload = snapshot["payload"]
            signature = str(snapshot["signature"])
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ExecutionRecoveryError("recovery_event_snapshot_corrupt") from exc
        if not isinstance(payload, Mapping) or not hmac.compare_digest(signature, _snapshot_signature(payload, self.receipt_store.signing_key)):
            raise ExecutionRecoveryError("recovery_event_snapshot_signature_invalid")
        current = self.audit_completion_events()
        expected = {"event_path": str(self.events.path), "event_ids": list(current["event_ids"]), "completion_receipt_ids": list(current["completion_receipt_ids"]), "chain_digest": current["chain_digest"], "count": current["count"]}
        for key, value in expected.items():
            if payload.get(key) != value:
                raise ExecutionRecoveryError("recovery_event_snapshot_drift")
        return {"status": "passed", "payload": dict(payload), "signature": signature}

    def verify_recovery_evidence(self) -> Mapping[str, Any]:
        """Verify recovery chain and its durable snapshot as a startup/replay gate."""
        chain = self.audit_completion_events()
        snapshot_path = self._completion_snapshot_path()
        if chain["count"] == 0 and not os.path.exists(snapshot_path):
            return {"status": "passed", "chain": chain, "snapshot": {"status": "not_run", "reason": "no_completion_events"}}
        if not os.path.exists(snapshot_path):
            raise ExecutionRecoveryError("recovery_event_snapshot_missing")
        snapshot = self.verify_completion_event_snapshot()
        return {"status": "passed", "chain": chain, "snapshot": snapshot}

    def recovery_evidence_status(self) -> Mapping[str, Any]:
        """Return an honest machine-readable status without hiding verification failures."""
        try:
            evidence = self.verify_recovery_evidence()
        except ExecutionRecoveryError as exc:
            return {"schema_version": "noesis.recovery-evidence-status.v1", "status": "blocked", "claim": False, "reason": str(exc)}
        snapshot = evidence.get("snapshot") or {}
        if snapshot.get("status") == "not_run":
            return {"schema_version": "noesis.recovery-evidence-status.v1", "status": "not_run", "claim": False, "reason": str(snapshot.get("reason", "no_completion_events")), "chain": evidence.get("chain")}
        return {"schema_version": "noesis.recovery-evidence-status.v1", "status": "passed", "claim": True, "chain": evidence.get("chain"), "snapshot": snapshot}

    def _status_snapshot_path(self) -> str:
        return str(self.events.path) + ".status.json"

    def persist_recovery_evidence_status(self) -> Mapping[str, Any]:
        """Atomically persist a signed machine-readable recovery status projection."""
        status = self.recovery_evidence_status()
        payload = {"schema_version": "noesis.recovery-evidence-status-snapshot.v1", "event_path": str(self.events.path), "status": status["status"], "claim": bool(status["claim"]), "reason": str(status.get("reason", "")), "chain_digest": str((status.get("chain") or {}).get("chain_digest", ""))}
        snapshot = {"payload": payload, "signature": _snapshot_signature(payload, self.receipt_store.signing_key)}
        _atomic_write_json(self._status_snapshot_path(), snapshot)
        return snapshot

    def verify_recovery_evidence_status_snapshot(self) -> Mapping[str, Any]:
        """Verify the persisted status projection against current recovery evidence."""
        try:
            with open(self._status_snapshot_path(), "r", encoding="utf-8") as handle:
                snapshot = json.load(handle)
            payload = snapshot["payload"]
            signature = str(snapshot["signature"])
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ExecutionRecoveryError("recovery_status_snapshot_corrupt") from exc
        if not isinstance(payload, Mapping) or not hmac.compare_digest(signature, _snapshot_signature(payload, self.receipt_store.signing_key)):
            raise ExecutionRecoveryError("recovery_status_snapshot_signature_invalid")
        current = self.recovery_evidence_status()
        expected = {"event_path": str(self.events.path), "status": current["status"], "claim": bool(current["claim"]), "reason": str(current.get("reason", "")), "chain_digest": str((current.get("chain") or {}).get("chain_digest", ""))}
        for key, value in expected.items():
            if payload.get(key) != value:
                raise ExecutionRecoveryError("recovery_status_snapshot_drift")
        return {"status": "passed", "payload": dict(payload), "signature": signature}

    def audit_replay_outcome(self, action: ExecutionRecoveryAction) -> Mapping[str, Any]:
        """Verify and describe the immutable evidence set supporting an exact replay."""
        existing = self._existing(action.action_id)
        if existing is None:
            raise ExecutionRecoveryError("recovery_replay_evidence_missing")
        action_digest = request_fingerprint(action.to_mapping())
        if existing.get("action_digest") != action_digest:
            raise ExecutionRecoveryError("recovery_action_replay_conflict")
        completion_receipt_id = str(existing.get("completion_receipt_id", ""))
        if not completion_receipt_id:
            raise ExecutionRecoveryError("recovery_completion_receipt_invalid")
        completion_receipt = self.receipt_store.get(completion_receipt_id)
        if completion_receipt is None or completion_receipt.outcome != "committed":
            raise ExecutionRecoveryError("recovery_completion_receipt_invalid")
        if not os.path.exists(self._status_snapshot_path()):
            raise ExecutionRecoveryError("recovery_status_snapshot_missing")
        status_snapshot = self.verify_recovery_evidence_status_snapshot()
        return {"schema_version": "noesis.recovery-replay-evidence.v1", "status": "passed", "claim": True, "action_id": action.action_id, "action_digest": action_digest, "completion_receipt_id": completion_receipt_id, "status_snapshot_digest": request_fingerprint(status_snapshot["payload"])}

    def handle(self, action: ExecutionRecoveryAction, context: Mapping[str, Any]) -> Mapping[str, Any]:
        self._authorize(context, action)
        existing = self._existing(action.action_id)
        action_digest = request_fingerprint(action.to_mapping())
        if existing is not None:
            replay_evidence = self.audit_replay_outcome(action)
            return {"status": "replayed", "result": existing, "replay_evidence": replay_evidence}
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
        self.persist_completion_event_snapshot()
        self.persist_recovery_evidence_status()
        return payload


__all__ = ["RECOVERY_ACTION_SCHEMA", "ExecutionRecoveryAction", "ExecutionRecoveryError", "ExecutionRecoveryExecutor", "_completion_event_digest"]
      
