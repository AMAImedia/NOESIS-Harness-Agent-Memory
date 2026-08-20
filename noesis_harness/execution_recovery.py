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
REPLAY_COMPLETENESS_SNAPSHOT_FIELDS = frozenset({"schema_version", "status", "event_count", "manifest_count", "catalog_count", "records", "completeness_digest", "completeness_path"})
REPLAY_COMPLETENESS_RECORD_FIELDS = frozenset({"action_id", "manifest_path", "action_digest", "completion_receipt_id", "catalog_record_digest"})


class _DuplicateJSONKeyError(ValueError):
    """Raised when a signed JSON record contains conflicting duplicate keys."""


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJSONKeyError(key)
        result[key] = value
    return result


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

    def audit_completion_events(self, target_action_id: str = "") -> Mapping[str, Any]:
        """Verify the hash-linked completion event chain and optionally return an action prefix."""
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
            event_action_id = str(payload.get("action_id", ""))
            if not event_action_id or event_action_id in seen_actions:
                raise ExecutionRecoveryError("recovery_completion_event_fork")
            if str(payload.get("previous_event_digest", "")) != last_digest:
                raise ExecutionRecoveryError("recovery_completion_event_chain_mismatch")
            completion_receipt_id = str(payload.get("completion_receipt_id", ""))
            if completion_receipt_id:
                receipt = self.receipt_store.get(completion_receipt_id)
                if receipt is None or receipt.outcome != "committed":
                    raise ExecutionRecoveryError("recovery_completion_receipt_invalid")
                receipt_ids.append(completion_receipt_id)
            seen_actions.add(event_action_id)
            event_id = str(event.get("event_id", ""))
            event_ids.append(event_id)
            last_digest = _completion_event_digest(payload)
            if target_action_id and target_action_id == event_action_id:
                return {"status": "passed", "count": len(event_ids), "event_ids": tuple(event_ids), "completion_receipt_ids": tuple(receipt_ids), "chain_digest": last_digest}
        if target_action_id:
            raise ExecutionRecoveryError("recovery_completion_action_missing")
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
                snapshot = json.load(handle, object_pairs_hook=_reject_duplicate_json_keys)
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

    def verify_recovery_evidence(self, action_id: str = "") -> Mapping[str, Any]:
        """Verify recovery chain and its durable snapshot as a startup/replay gate."""
        chain = self.audit_completion_events(action_id)
        snapshot_path = self._completion_snapshot_path()
        if chain["count"] == 0 and not os.path.exists(snapshot_path):
            return {"status": "passed", "chain": chain, "snapshot": {"status": "not_run", "reason": "no_completion_events"}}
        if not os.path.exists(snapshot_path):
            raise ExecutionRecoveryError("recovery_event_snapshot_missing")
        snapshot = self.verify_completion_event_snapshot()
        return {"status": "passed", "chain": chain, "snapshot": snapshot}

    def recovery_evidence_status(self, action_id: str = "") -> Mapping[str, Any]:
        """Return an honest machine-readable status without hiding verification failures."""
        try:
            evidence = self.verify_recovery_evidence(action_id)
        except ExecutionRecoveryError as exc:
            return {"schema_version": "noesis.recovery-evidence-status.v1", "status": "blocked", "claim": False, "reason": str(exc)}
        snapshot = evidence.get("snapshot") or {}
        if snapshot.get("status") == "not_run":
            return {"schema_version": "noesis.recovery-evidence-status.v1", "status": "not_run", "claim": False, "reason": str(snapshot.get("reason", "no_completion_events")), "chain": evidence.get("chain")}
        return {"schema_version": "noesis.recovery-evidence-status.v1", "status": "passed", "claim": True, "chain": evidence.get("chain"), "snapshot": snapshot}

    def _status_snapshot_path(self, action_id: str = "") -> str:
        if not action_id:
            return str(self.events.path) + ".status.json"
        action_key = request_fingerprint({"action_id": str(action_id)}).replace(":", "_")
        return str(self.events.path) + ".status." + action_key + ".json"

    def persist_recovery_evidence_status(self, action_id: str = "") -> Mapping[str, Any]:
        """Atomically persist a signed machine-readable recovery status projection."""
        status = self.recovery_evidence_status(action_id)
        payload = {"schema_version": "noesis.recovery-evidence-status-snapshot.v1", "event_path": str(self.events.path), "action_id": str(action_id), "status": status["status"], "claim": bool(status["claim"]), "reason": str(status.get("reason", "")), "chain_digest": str((status.get("chain") or {}).get("chain_digest", ""))}
        snapshot = {"payload": payload, "signature": _snapshot_signature(payload, self.receipt_store.signing_key)}
        _atomic_write_json(self._status_snapshot_path(action_id), snapshot)
        return snapshot

    def verify_recovery_evidence_status_snapshot(self, action_id: str = "") -> Mapping[str, Any]:
        """Verify the persisted status projection against current recovery evidence."""
        try:
            with open(self._status_snapshot_path(action_id), "r", encoding="utf-8") as handle:
                snapshot = json.load(handle)
            payload = snapshot["payload"]
            signature = str(snapshot["signature"])
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ExecutionRecoveryError("recovery_status_snapshot_corrupt") from exc
        if not isinstance(payload, Mapping) or not hmac.compare_digest(signature, _snapshot_signature(payload, self.receipt_store.signing_key)):
            raise ExecutionRecoveryError("recovery_status_snapshot_signature_invalid")
        current = self.recovery_evidence_status(action_id)
        expected = {"event_path": str(self.events.path), "action_id": str(action_id), "status": current["status"], "claim": bool(current["claim"]), "reason": str(current.get("reason", "")), "chain_digest": str((current.get("chain") or {}).get("chain_digest", ""))}
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
        chain = self.audit_completion_events(action.action_id)
        if not chain["completion_receipt_ids"] or chain["completion_receipt_ids"][-1] != completion_receipt_id:
            raise ExecutionRecoveryError("recovery_replay_event_receipt_binding")
        if not os.path.exists(self._status_snapshot_path(action.action_id)):
            raise ExecutionRecoveryError("recovery_status_snapshot_missing")
        status_snapshot = self.verify_recovery_evidence_status_snapshot(action.action_id)
        return {"schema_version": "noesis.recovery-replay-evidence.v1", "status": "passed", "claim": True, "action_id": action.action_id, "action_digest": action_digest, "completion_receipt_id": completion_receipt_id, "event_chain_digest": chain["chain_digest"], "status_snapshot_digest": request_fingerprint(status_snapshot["payload"])}

    def _replay_snapshot_path(self, action_id: str) -> str:
        action_key = request_fingerprint({"action_id": str(action_id)}).replace(":", "_")
        return str(self.events.path) + ".replay." + action_key + ".json"

    def persist_replay_outcome_snapshot(self, action: ExecutionRecoveryAction) -> Mapping[str, Any]:
        """Atomically persist signed evidence for a future exact replay."""
        evidence = self.audit_replay_outcome(action)
        payload = dict(evidence)
        payload["schema_version"] = "noesis.recovery-replay-evidence-snapshot.v1"
        payload["snapshot_path"] = self._replay_snapshot_path(action.action_id)
        snapshot = {"payload": payload, "signature": _snapshot_signature(payload, self.receipt_store.signing_key)}
        _atomic_write_json(self._replay_snapshot_path(action.action_id), snapshot)
        return snapshot

    def verify_replay_outcome_snapshot(self, action: ExecutionRecoveryAction) -> Mapping[str, Any]:
        """Verify the durable replay evidence snapshot against current immutable evidence."""
        try:
            with open(self._replay_snapshot_path(action.action_id), "r", encoding="utf-8") as handle:
                snapshot = json.load(handle, object_pairs_hook=_reject_duplicate_json_keys)
            payload = snapshot["payload"]
            signature = str(snapshot["signature"])
        except _DuplicateJSONKeyError as exc:
            raise ExecutionRecoveryError("recovery_replay_snapshot_duplicate_record") from exc
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ExecutionRecoveryError("recovery_replay_snapshot_corrupt") from exc
        if not isinstance(payload, Mapping) or not hmac.compare_digest(signature, _snapshot_signature(payload, self.receipt_store.signing_key)):
            raise ExecutionRecoveryError("recovery_replay_snapshot_signature_invalid")
        expected_path = self._replay_snapshot_path(action.action_id)
        if payload.get("snapshot_path") != expected_path:
            raise ExecutionRecoveryError("recovery_replay_snapshot_path_mismatch")
        current = self.audit_replay_outcome(action)
        for key in ("action_id", "action_digest", "completion_receipt_id"):
            if payload.get(key) != current.get(key):
                raise ExecutionRecoveryError("recovery_replay_snapshot_identity_conflict")
        for key, value in current.items():
            if key == "schema_version" or key in {"action_id", "action_digest", "completion_receipt_id"}:
                continue
            if payload.get(key) != value:
                raise ExecutionRecoveryError("recovery_replay_snapshot_drift")
        return {"status": "passed", "payload": dict(payload), "signature": signature}

    def audit_replay_snapshot_inventory(self, action: ExecutionRecoveryAction) -> Mapping[str, Any]:
        """Return a deterministic inventory for the verified replay snapshot."""
        verified = self.verify_replay_outcome_snapshot(action)
        payload = verified["payload"]
        return {"schema_version": "noesis.recovery-replay-snapshot-inventory.v1", "status": "passed", "snapshot_path": self._replay_snapshot_path(action.action_id), "snapshot_digest": request_fingerprint(payload), "action_id": str(payload.get("action_id", "")), "action_digest": str(payload.get("action_digest", "")), "completion_receipt_id": str(payload.get("completion_receipt_id", ""))}

    def _replay_inventory_snapshot_path(self, action_id: str) -> str:
        return self._replay_snapshot_path(action_id) + ".inventory.json"

    def persist_replay_snapshot_inventory(self, action: ExecutionRecoveryAction) -> Mapping[str, Any]:
        """Atomically persist signed evidence for the verified replay inventory."""
        inventory = self.audit_replay_snapshot_inventory(action)
        payload = dict(inventory)
        payload["schema_version"] = "noesis.recovery-replay-snapshot-inventory-snapshot.v1"
        payload["inventory_path"] = self._replay_inventory_snapshot_path(action.action_id)
        snapshot = {"payload": payload, "signature": _snapshot_signature(payload, self.receipt_store.signing_key)}
        _atomic_write_json(self._replay_inventory_snapshot_path(action.action_id), snapshot)
        return snapshot

    def verify_replay_snapshot_inventory_snapshot(self, action: ExecutionRecoveryAction) -> Mapping[str, Any]:
        """Verify durable replay inventory evidence against current immutable evidence."""
        try:
            with open(self._replay_inventory_snapshot_path(action.action_id), "r", encoding="utf-8") as handle:
                snapshot = json.load(handle, object_pairs_hook=_reject_duplicate_json_keys)
            payload = snapshot["payload"]
            signature = str(snapshot["signature"])
        except _DuplicateJSONKeyError as exc:
            raise ExecutionRecoveryError("recovery_replay_inventory_snapshot_duplicate_record") from exc
        except FileNotFoundError as exc:
            raise ExecutionRecoveryError("recovery_replay_inventory_snapshot_missing") from exc
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ExecutionRecoveryError("recovery_replay_inventory_snapshot_corrupt") from exc
        if not isinstance(payload, Mapping) or not hmac.compare_digest(signature, _snapshot_signature(payload, self.receipt_store.signing_key)):
            raise ExecutionRecoveryError("recovery_replay_inventory_snapshot_signature_invalid")
        if payload.get("inventory_path") != self._replay_inventory_snapshot_path(action.action_id):
            raise ExecutionRecoveryError("recovery_replay_inventory_snapshot_path_mismatch")
        current = self.audit_replay_snapshot_inventory(action)
        for key, value in current.items():
            if key == "schema_version":
                continue
            if payload.get(key) != value:
                raise ExecutionRecoveryError("recovery_replay_inventory_snapshot_drift")
        return {"status": "passed", "payload": dict(payload), "signature": signature}

    def audit_replay_evidence_catalog(self) -> Mapping[str, Any]:
        """Audit every action-scoped replay inventory sidecar without creating state."""
        parent = os.path.dirname(os.path.abspath(str(self.events.path))) or "."
        base = os.path.basename(str(self.events.path)) + ".replay."
        suffix = ".json.inventory.json"
        candidates = sorted(name for name in os.listdir(parent) if name.startswith(base) and name.endswith(suffix))
        records = []
        seen_actions = set()
        events_by_action = {}
        for event in self.events.iter_events():
            if event.get("type") == "execution_recovery_completed":
                event_payload = event.get("payload")
                if isinstance(event_payload, Mapping):
                    events_by_action[str(event_payload.get("action_id", ""))] = dict(event_payload)
        for name in candidates:
            inventory_path = os.path.join(parent, name)
            try:
                with open(inventory_path, "r", encoding="utf-8") as handle:
                    snapshot = json.load(handle, object_pairs_hook=_reject_duplicate_json_keys)
                payload = snapshot["payload"]
                signature = str(snapshot["signature"])
            except _DuplicateJSONKeyError as exc:
                raise ExecutionRecoveryError("recovery_replay_catalog_duplicate_record") from exc
            except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ExecutionRecoveryError("recovery_replay_catalog_corrupt") from exc
            if not isinstance(payload, Mapping) or not hmac.compare_digest(signature, _snapshot_signature(payload, self.receipt_store.signing_key)):
                raise ExecutionRecoveryError("recovery_replay_catalog_signature_invalid")
            action_id = str(payload.get("action_id", ""))
            if not action_id or action_id in seen_actions:
                raise ExecutionRecoveryError("recovery_replay_catalog_duplicate_action")
            seen_actions.add(action_id)
            if os.path.abspath(str(payload.get("inventory_path", ""))) != os.path.abspath(inventory_path):
                raise ExecutionRecoveryError("recovery_replay_catalog_inventory_path_mismatch")
            replay_path = inventory_path[: -len(".inventory.json")]
            if os.path.abspath(str(payload.get("snapshot_path", ""))) != os.path.abspath(replay_path):
                raise ExecutionRecoveryError("recovery_replay_catalog_snapshot_path_mismatch")
            try:
                with open(replay_path, "r", encoding="utf-8") as handle:
                    replay_snapshot = json.load(handle, object_pairs_hook=_reject_duplicate_json_keys)
                replay_payload = replay_snapshot["payload"]
                replay_signature = str(replay_snapshot["signature"])
            except _DuplicateJSONKeyError as exc:
                raise ExecutionRecoveryError("recovery_replay_catalog_duplicate_record") from exc
            except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ExecutionRecoveryError("recovery_replay_catalog_replay_missing") from exc
            if not isinstance(replay_payload, Mapping) or not hmac.compare_digest(replay_signature, _snapshot_signature(replay_payload, self.receipt_store.signing_key)):
                raise ExecutionRecoveryError("recovery_replay_catalog_replay_signature_invalid")
            event_payload = events_by_action.get(action_id)
            if event_payload is None or replay_payload.get("action_id") != action_id or payload.get("action_digest") != replay_payload.get("action_digest") or event_payload.get("action_digest") != replay_payload.get("action_digest"):
                raise ExecutionRecoveryError("recovery_replay_catalog_identity_conflict")
            receipt_id = str(payload.get("completion_receipt_id", ""))
            if receipt_id != str(event_payload.get("completion_receipt_id", "")):
                raise ExecutionRecoveryError("recovery_replay_catalog_receipt_conflict")
            receipt = self.receipt_store.get(receipt_id)
            if receipt is None or receipt.outcome != "committed":
                raise ExecutionRecoveryError("recovery_replay_catalog_receipt_invalid")
            status_path = self._status_snapshot_path(action_id)
            try:
                with open(status_path, "r", encoding="utf-8") as handle:
                    status_snapshot = json.load(handle, object_pairs_hook=_reject_duplicate_json_keys)
                status_payload = status_snapshot["payload"]
                status_signature = str(status_snapshot["signature"])
            except _DuplicateJSONKeyError as exc:
                raise ExecutionRecoveryError("recovery_replay_catalog_duplicate_record") from exc
            except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ExecutionRecoveryError("recovery_replay_catalog_status_missing") from exc
            if not isinstance(status_payload, Mapping) or not hmac.compare_digest(status_signature, _snapshot_signature(status_payload, self.receipt_store.signing_key)):
                raise ExecutionRecoveryError("recovery_replay_catalog_status_signature_invalid")
            if status_payload.get("action_id") != action_id or replay_payload.get("status_snapshot_digest") != request_fingerprint(status_payload):
                raise ExecutionRecoveryError("recovery_replay_catalog_status_conflict")
            records.append({"action_id": action_id, "inventory_path": inventory_path, "snapshot_path": replay_path, "snapshot_digest": request_fingerprint(replay_payload), "completion_receipt_id": receipt_id})
        return {"schema_version": "noesis.recovery-replay-evidence-catalog.v1", "status": "passed", "count": len(records), "records": records, "catalog_digest": request_fingerprint({"records": records})}

    def _replay_catalog_snapshot_path(self) -> str:
        return str(self.events.path) + ".replay-catalog.json"

    def persist_replay_evidence_catalog(self) -> Mapping[str, Any]:
        """Atomically persist signed evidence for the verified replay catalog."""
        catalog = self.audit_replay_evidence_catalog()
        payload = dict(catalog)
        payload["schema_version"] = "noesis.recovery-replay-evidence-catalog-snapshot.v1"
        payload["catalog_path"] = self._replay_catalog_snapshot_path()
        snapshot = {"payload": payload, "signature": _snapshot_signature(payload, self.receipt_store.signing_key)}
        _atomic_write_json(self._replay_catalog_snapshot_path(), snapshot)
        return snapshot

    def verify_replay_evidence_catalog_snapshot(self) -> Mapping[str, Any]:
        """Verify durable catalog evidence against current action-scoped records."""
        try:
            with open(self._replay_catalog_snapshot_path(), "r", encoding="utf-8") as handle:
                snapshot = json.load(handle, object_pairs_hook=_reject_duplicate_json_keys)
            payload = snapshot["payload"]
            signature = str(snapshot["signature"])
        except _DuplicateJSONKeyError as exc:
            raise ExecutionRecoveryError("recovery_replay_catalog_snapshot_duplicate_record") from exc
        except FileNotFoundError as exc:
            raise ExecutionRecoveryError("recovery_replay_catalog_snapshot_missing") from exc
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ExecutionRecoveryError("recovery_replay_catalog_snapshot_corrupt") from exc
        if not isinstance(payload, Mapping) or not hmac.compare_digest(signature, _snapshot_signature(payload, self.receipt_store.signing_key)):
            raise ExecutionRecoveryError("recovery_replay_catalog_snapshot_signature_invalid")
        if payload.get("catalog_path") != self._replay_catalog_snapshot_path():
            raise ExecutionRecoveryError("recovery_replay_catalog_snapshot_path_mismatch")
        catalog_records = payload.get("records")
        if not isinstance(catalog_records, list) or any(not isinstance(record, Mapping) for record in catalog_records):
            raise ExecutionRecoveryError("recovery_replay_catalog_snapshot_records_invalid")
        catalog_ids = [str(record.get("action_id", "")) for record in catalog_records]
        if any(not action_id for action_id in catalog_ids) or len(set(catalog_ids)) != len(catalog_ids):
            raise ExecutionRecoveryError("recovery_replay_catalog_snapshot_duplicate_action")
        current = self.audit_replay_evidence_catalog()
        for key, value in current.items():
            if key == "schema_version":
                continue
            if payload.get(key) != value:
                raise ExecutionRecoveryError("recovery_replay_catalog_snapshot_drift")
        return {"status": "passed", "payload": dict(payload), "signature": signature}

    def _replay_commit_manifest_path(self, action_id: str) -> str:
        action_key = request_fingerprint({"action_id": str(action_id)}).replace(":", "_")
        return str(self.events.path) + ".replay-commit." + action_key + ".json"

    @staticmethod
    def _replay_completeness_record_digest(action: ExecutionRecoveryAction, replay_evidence: Mapping[str, Any], catalog_record: Mapping[str, Any], manifest_path: str) -> str:
        return request_fingerprint({"action_id": action.action_id, "action_digest": str(replay_evidence.get("action_digest", "")), "completion_receipt_id": str(replay_evidence.get("completion_receipt_id", "")), "catalog_record_digest": request_fingerprint(catalog_record), "manifest_path": str(manifest_path)})

    @staticmethod
    def _replay_bundle_digest(payload: Mapping[str, Any]) -> str:
        return request_fingerprint({str(key): value for key, value in payload.items() if str(key) != "bundle_digest"})

    def persist_replay_evidence_commit_manifest(self, action: ExecutionRecoveryAction) -> Mapping[str, Any]:
        """Persist the final signed marker for a complete replay evidence bundle."""
        replay_evidence = self.audit_replay_outcome(action)
        status_snapshot = self.verify_recovery_evidence_status_snapshot(action.action_id)
        replay_snapshot = self.verify_replay_outcome_snapshot(action)
        inventory_snapshot = self.verify_replay_snapshot_inventory_snapshot(action)
        catalog_snapshot = self.verify_replay_evidence_catalog_snapshot()
        catalog_record = next((record for record in catalog_snapshot["payload"].get("records", ()) if str(record.get("action_id", "")) == action.action_id), None)
        if catalog_record is None:
            raise ExecutionRecoveryError("recovery_replay_commit_manifest_catalog_record_missing")
        completeness_snapshot = None
        if os.path.exists(self._replay_completeness_snapshot_path()):
            try:
                completeness_snapshot = self.verify_replay_evidence_completeness_snapshot()
            except ExecutionRecoveryError as exc:
                if str(exc) != "recovery_replay_completeness_manifest_missing":
                    raise
        manifest_path = self._replay_commit_manifest_path(action.action_id)
        payload = {"schema_version": "noesis.recovery-replay-evidence-commit-manifest.v1", "action_id": action.action_id, "action_digest": replay_evidence["action_digest"], "completion_receipt_id": replay_evidence["completion_receipt_id"], "event_path": str(self.events.path), "status_snapshot_path": self._status_snapshot_path(action.action_id), "replay_snapshot_path": self._replay_snapshot_path(action.action_id), "inventory_snapshot_path": self._replay_inventory_snapshot_path(action.action_id), "catalog_snapshot_path": self._replay_catalog_snapshot_path(), "completeness_snapshot_path": self._replay_completeness_snapshot_path(), "status_snapshot_digest": request_fingerprint(status_snapshot["payload"]), "replay_snapshot_digest": request_fingerprint(replay_snapshot["payload"]), "inventory_snapshot_digest": request_fingerprint(inventory_snapshot["payload"]), "catalog_record_digest": request_fingerprint(catalog_record), "completeness_record_digest": self._replay_completeness_record_digest(action, replay_evidence, catalog_record, manifest_path)}
        payload["bundle_digest"] = self._replay_bundle_digest(payload)
        snapshot = {"payload": payload, "signature": _snapshot_signature(payload, self.receipt_store.signing_key)}
        _atomic_write_json(self._replay_commit_manifest_path(action.action_id), snapshot)
        return snapshot

    def verify_replay_evidence_commit_manifest(self, action: ExecutionRecoveryAction) -> Mapping[str, Any]:
        """Verify the signed last-write marker and every evidence bundle member."""
        try:
            with open(self._replay_commit_manifest_path(action.action_id), "r", encoding="utf-8") as handle:
                snapshot = json.load(handle, object_pairs_hook=_reject_duplicate_json_keys)
            payload = snapshot["payload"]
            signature = str(snapshot["signature"])
        except _DuplicateJSONKeyError as exc:
            raise ExecutionRecoveryError("recovery_replay_commit_manifest_duplicate_record") from exc
        except FileNotFoundError as exc:
            raise ExecutionRecoveryError("recovery_replay_commit_manifest_missing") from exc
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ExecutionRecoveryError("recovery_replay_commit_manifest_corrupt") from exc
        if not isinstance(payload, Mapping) or not hmac.compare_digest(signature, _snapshot_signature(payload, self.receipt_store.signing_key)):
            raise ExecutionRecoveryError("recovery_replay_commit_manifest_signature_invalid")
        expected_paths = {"event_path": str(self.events.path), "status_snapshot_path": self._status_snapshot_path(action.action_id), "replay_snapshot_path": self._replay_snapshot_path(action.action_id), "inventory_snapshot_path": self._replay_inventory_snapshot_path(action.action_id), "catalog_snapshot_path": self._replay_catalog_snapshot_path(), "completeness_snapshot_path": self._replay_completeness_snapshot_path()}
        for key, value in expected_paths.items():
            if payload.get(key) != value:
                raise ExecutionRecoveryError("recovery_replay_commit_manifest_path_mismatch")
        replay_evidence = self.audit_replay_outcome(action)
        status_snapshot = self.verify_recovery_evidence_status_snapshot(action.action_id)
        replay_snapshot = self.verify_replay_outcome_snapshot(action)
        inventory_snapshot = self.verify_replay_snapshot_inventory_snapshot(action)
        catalog_snapshot = self.verify_replay_evidence_catalog_snapshot()
        catalog_record = next((record for record in catalog_snapshot["payload"].get("records", ()) if str(record.get("action_id", "")) == action.action_id), None)
        if catalog_record is None:
            raise ExecutionRecoveryError("recovery_replay_commit_manifest_catalog_record_missing")
        expected = {"schema_version": "noesis.recovery-replay-evidence-commit-manifest.v1", "action_id": action.action_id, "action_digest": replay_evidence["action_digest"], "completion_receipt_id": replay_evidence["completion_receipt_id"], "event_path": str(self.events.path), "status_snapshot_path": self._status_snapshot_path(action.action_id), "replay_snapshot_path": self._replay_snapshot_path(action.action_id), "inventory_snapshot_path": self._replay_inventory_snapshot_path(action.action_id), "catalog_snapshot_path": self._replay_catalog_snapshot_path(), "completeness_snapshot_path": self._replay_completeness_snapshot_path(), "status_snapshot_digest": request_fingerprint(status_snapshot["payload"]), "replay_snapshot_digest": request_fingerprint(replay_snapshot["payload"]), "inventory_snapshot_digest": request_fingerprint(inventory_snapshot["payload"]), "catalog_record_digest": request_fingerprint(catalog_record), "completeness_record_digest": self._replay_completeness_record_digest(action, replay_evidence, catalog_record, self._replay_commit_manifest_path(action.action_id))}
        expected["bundle_digest"] = self._replay_bundle_digest(expected)
        for key, value in expected.items():
            if payload.get(key) != value:
                raise ExecutionRecoveryError("recovery_replay_commit_manifest_drift")
        self.verify_replay_evidence_completeness_snapshot()
        return {"status": "passed", "payload": dict(payload), "signature": signature}

    def audit_replay_evidence_completeness(self, *, require_durable_snapshot: bool = False) -> Mapping[str, Any]:
        """Audit replay evidence, optionally requiring the durable signed completeness snapshot."""
        parent = os.path.dirname(os.path.abspath(str(self.events.path))) or "."
        base = os.path.basename(str(self.events.path)) + ".replay-commit."
        expected = {}
        for event in self.events.iter_events():
            if event.get("type") == "execution_recovery_completed":
                payload = event.get("payload")
                if not isinstance(payload, Mapping):
                    raise ExecutionRecoveryError("recovery_replay_completeness_event_corrupt")
                action_id = str(payload.get("action_id", ""))
                if not action_id or action_id in expected:
                    raise ExecutionRecoveryError("recovery_replay_completeness_duplicate_action")
                expected[action_id] = dict(payload)
        candidates = sorted(name for name in os.listdir(parent) if name.startswith(base) and name.endswith(".json"))
        expected_manifest_names = {os.path.basename(self._replay_commit_manifest_path(action_id)) for action_id in expected}
        if len(expected_manifest_names) != len(expected):
            raise ExecutionRecoveryError("recovery_replay_completeness_manifest_path_collision")
        unknown_manifest_names = set(candidates) - expected_manifest_names
        if unknown_manifest_names:
            raise ExecutionRecoveryError("recovery_replay_completeness_orphan_manifest")
        expected_sidecar_paths = {self._completion_snapshot_path(), self._status_snapshot_path(), self._replay_catalog_snapshot_path(), self._replay_completeness_snapshot_path()}
        for action_id in expected:
            expected_sidecar_paths.update({self._status_snapshot_path(action_id), self._replay_snapshot_path(action_id), self._replay_inventory_snapshot_path(action_id), self._replay_commit_manifest_path(action_id)})
        sidecar_prefix = os.path.basename(str(self.events.path)) + "."
        sidecar_candidates = {name for name in os.listdir(parent) if name.startswith(sidecar_prefix) and name.endswith(".json")}
        expected_sidecar_names = {os.path.basename(path) for path in expected_sidecar_paths}
        if sidecar_candidates - expected_sidecar_names:
            raise ExecutionRecoveryError("recovery_replay_completeness_orphan_sidecar")
        records = []
        seen = set()
        parent_real = os.path.realpath(parent)
        for name in candidates:
            manifest_path = os.path.join(parent, name)
            if os.path.islink(manifest_path) or os.path.realpath(manifest_path) != os.path.join(parent_real, name):
                raise ExecutionRecoveryError("recovery_replay_completeness_manifest_alias")
            try:
                if os.stat(manifest_path).st_nlink != 1:
                    raise ExecutionRecoveryError("recovery_replay_completeness_manifest_file_identity")
            except FileNotFoundError as exc:
                raise ExecutionRecoveryError("recovery_replay_completeness_manifest_missing") from exc
            try:
                with open(manifest_path, "r", encoding="utf-8") as handle:
                    snapshot = json.load(handle, object_pairs_hook=_reject_duplicate_json_keys)
                payload = snapshot["payload"]
                signature = str(snapshot["signature"])
            except _DuplicateJSONKeyError as exc:
                raise ExecutionRecoveryError("recovery_replay_completeness_duplicate_record") from exc
            except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ExecutionRecoveryError("recovery_replay_completeness_corrupt") from exc
            if not isinstance(payload, Mapping) or not hmac.compare_digest(signature, _snapshot_signature(payload, self.receipt_store.signing_key)):
                raise ExecutionRecoveryError("recovery_replay_completeness_signature_invalid")
            action_id = str(payload.get("action_id", ""))
            if not action_id or action_id in seen:
                raise ExecutionRecoveryError("recovery_replay_completeness_duplicate_action")
            seen.add(action_id)
            if os.path.abspath(manifest_path) != os.path.abspath(self._replay_commit_manifest_path(action_id)):
                raise ExecutionRecoveryError("recovery_replay_completeness_path_mismatch")
            if payload.get("bundle_digest") != self._replay_bundle_digest(payload):
                raise ExecutionRecoveryError("recovery_replay_completeness_bundle_digest_mismatch")
            expected_paths = {"event_path": str(self.events.path), "status_snapshot_path": self._status_snapshot_path(action_id), "replay_snapshot_path": self._replay_snapshot_path(action_id), "inventory_snapshot_path": self._replay_inventory_snapshot_path(action_id), "catalog_snapshot_path": self._replay_catalog_snapshot_path(), "completeness_snapshot_path": self._replay_completeness_snapshot_path()}
            for field, expected_path in expected_paths.items():
                if payload.get(field) != expected_path:
                    raise ExecutionRecoveryError("recovery_replay_completeness_path_mismatch")
                expected_abs = os.path.abspath(expected_path)
                expected_real = os.path.realpath(expected_path)
                try:
                    if os.path.commonpath((parent_real, expected_abs)) != parent_real or os.path.commonpath((parent_real, expected_real)) != parent_real:
                        raise ExecutionRecoveryError("recovery_replay_completeness_path_containment")
                except ValueError as exc:
                    raise ExecutionRecoveryError("recovery_replay_completeness_path_containment") from exc
                if os.path.islink(expected_path):
                    raise ExecutionRecoveryError("recovery_replay_completeness_sidecar_alias")
                if os.path.isfile(expected_path) and os.stat(expected_path).st_nlink != 1:
                    raise ExecutionRecoveryError("recovery_replay_completeness_sidecar_file_identity")
                if not os.path.isfile(expected_path) and field != "completeness_snapshot_path":
                    raise ExecutionRecoveryError("recovery_replay_completeness_bundle_path_missing")
                if field != "event_path" and os.path.isfile(expected_path):
                    try:
                        with open(expected_path, "r", encoding="utf-8") as handle:
                            sidecar = json.load(handle, object_pairs_hook=_reject_duplicate_json_keys)
                        sidecar_payload = sidecar["payload"]
                        sidecar_signature = str(sidecar["signature"])
                    except _DuplicateJSONKeyError as exc:
                        raise ExecutionRecoveryError("recovery_replay_completeness_sidecar_duplicate_record") from exc
                    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                        raise ExecutionRecoveryError("recovery_replay_completeness_sidecar_corrupt") from exc
                    if not isinstance(sidecar_payload, Mapping) or not hmac.compare_digest(sidecar_signature, _snapshot_signature(sidecar_payload, self.receipt_store.signing_key)):
                        raise ExecutionRecoveryError("recovery_replay_completeness_sidecar_signature_invalid")
                    if field in {"status_snapshot_path", "replay_snapshot_path", "inventory_snapshot_path"}:
                        if str(sidecar_payload.get("action_id", "")) != action_id:
                            raise ExecutionRecoveryError("recovery_replay_completeness_sidecar_identity_conflict")
                        digest_field = {"status_snapshot_path": "status_snapshot_digest", "replay_snapshot_path": "replay_snapshot_digest", "inventory_snapshot_path": "inventory_snapshot_digest"}[field]
                        if payload.get(digest_field) != request_fingerprint(sidecar_payload):
                            raise ExecutionRecoveryError("recovery_replay_completeness_sidecar_digest_mismatch")
            event_payload = expected.get(action_id)
            if event_payload is None or payload.get("action_digest") != event_payload.get("action_digest") or payload.get("completion_receipt_id") != event_payload.get("completion_receipt_id"):
                raise ExecutionRecoveryError("recovery_replay_completeness_identity_conflict")
            receipt = self.receipt_store.get(str(payload.get("completion_receipt_id", "")))
            if receipt is None or receipt.outcome != "committed":
                raise ExecutionRecoveryError("recovery_replay_completeness_receipt_invalid")
            records.append({"action_id": action_id, "manifest_path": manifest_path, "action_digest": str(payload.get("action_digest", "")), "completion_receipt_id": str(payload.get("completion_receipt_id", "")), "catalog_record_digest": str(payload.get("catalog_record_digest", ""))})
        if set(expected) != seen:
            raise ExecutionRecoveryError("recovery_replay_completeness_manifest_missing")
        catalog = self.audit_replay_evidence_catalog()
        catalog_snapshot = self.verify_replay_evidence_catalog_snapshot()
        if int(catalog.get("count", 0)) != len(expected):
            raise ExecutionRecoveryError("recovery_replay_completeness_catalog_mismatch")
        catalog_records = {str(record.get("action_id", "")): record for record in catalog_snapshot["payload"].get("records", ())}
        for record in records:
            catalog_record = catalog_records.get(record["action_id"])
            if catalog_record is None or record["catalog_record_digest"] != request_fingerprint(catalog_record):
                raise ExecutionRecoveryError("recovery_replay_completeness_catalog_record_mismatch")
        result = {"schema_version": "noesis.recovery-replay-evidence-completeness.v1", "status": "passed", "event_count": len(expected), "manifest_count": len(records), "catalog_count": int(catalog["count"]), "records": records, "completeness_digest": request_fingerprint({"records": records, "catalog_digest": catalog["catalog_digest"]})}
        if require_durable_snapshot:
            try:
                self.verify_replay_evidence_completeness_snapshot()
            except ExecutionRecoveryError as exc:
                if str(exc) == "recovery_replay_completeness_snapshot_missing":
                    raise ExecutionRecoveryError("recovery_replay_completeness_snapshot_required") from exc
                raise
        return result

    def _replay_completeness_snapshot_path(self) -> str:
        return str(self.events.path) + ".replay-completeness.json"

    def persist_replay_evidence_completeness(self) -> Mapping[str, Any]:
        """Atomically persist signed completeness evidence for the replay bundle."""
        completeness = self.audit_replay_evidence_completeness()
        payload = dict(completeness)
        payload["schema_version"] = "noesis.recovery-replay-evidence-completeness-snapshot.v1"
        payload["completeness_path"] = self._replay_completeness_snapshot_path()
        snapshot = {"payload": payload, "signature": _snapshot_signature(payload, self.receipt_store.signing_key)}
        _atomic_write_json(self._replay_completeness_snapshot_path(), snapshot)
        return snapshot

    def verify_replay_evidence_completeness_snapshot(self) -> Mapping[str, Any]:
        """Verify durable completeness evidence against the current bundle."""
        try:
            with open(self._replay_completeness_snapshot_path(), "r", encoding="utf-8") as handle:
                snapshot = json.load(handle, object_pairs_hook=_reject_duplicate_json_keys)
            payload = snapshot["payload"]
            signature = str(snapshot["signature"])
        except _DuplicateJSONKeyError as exc:
            raise ExecutionRecoveryError("recovery_replay_completeness_snapshot_duplicate_record") from exc
        except FileNotFoundError as exc:
            raise ExecutionRecoveryError("recovery_replay_completeness_snapshot_missing") from exc
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ExecutionRecoveryError("recovery_replay_completeness_snapshot_corrupt") from exc
        if not isinstance(payload, Mapping) or not hmac.compare_digest(signature, _snapshot_signature(payload, self.receipt_store.signing_key)):
            raise ExecutionRecoveryError("recovery_replay_completeness_snapshot_signature_invalid")
        unknown_fields = set(payload) - REPLAY_COMPLETENESS_SNAPSHOT_FIELDS
        missing_fields = REPLAY_COMPLETENESS_SNAPSHOT_FIELDS - set(payload)
        if unknown_fields:
            raise ExecutionRecoveryError("recovery_replay_completeness_snapshot_unknown_field")
        if missing_fields:
            raise ExecutionRecoveryError("recovery_replay_completeness_snapshot_missing_field")
        if payload.get("schema_version") != "noesis.recovery-replay-evidence-completeness-snapshot.v1":
            raise ExecutionRecoveryError("recovery_replay_completeness_snapshot_schema_invalid")
        if payload.get("status") != "passed":
            raise ExecutionRecoveryError("recovery_replay_completeness_snapshot_status_invalid")
        if payload.get("completeness_path") != self._replay_completeness_snapshot_path():
            raise ExecutionRecoveryError("recovery_replay_completeness_snapshot_path_mismatch")
        records = payload.get("records")
        if not isinstance(records, list) or any(not isinstance(record, Mapping) for record in records):
            raise ExecutionRecoveryError("recovery_replay_completeness_snapshot_records_invalid")
        for record in records:
            if set(record) != REPLAY_COMPLETENESS_RECORD_FIELDS:
                raise ExecutionRecoveryError("recovery_replay_completeness_snapshot_record_schema_invalid")
        record_ids = [str(record.get("action_id", "")) for record in records]
        if any(not action_id for action_id in record_ids) or len(set(record_ids)) != len(record_ids):
            raise ExecutionRecoveryError("recovery_replay_completeness_snapshot_duplicate_action")
        count_fields = ("event_count", "manifest_count", "catalog_count")
        if any(not isinstance(payload.get(field), int) or isinstance(payload.get(field), bool) or payload.get(field) < 0 for field in count_fields):
            raise ExecutionRecoveryError("recovery_replay_completeness_snapshot_counts_invalid")
        if payload.get("manifest_count") != len(records):
            raise ExecutionRecoveryError("recovery_replay_completeness_snapshot_counts_mismatch")
        if not isinstance(payload.get("completeness_digest"), str) or not payload.get("completeness_digest"):
            raise ExecutionRecoveryError("recovery_replay_completeness_snapshot_digest_invalid")
        current = self.audit_replay_evidence_completeness()
        for key, value in current.items():
            if key == "schema_version":
                continue
            if payload.get(key) != value:
                raise ExecutionRecoveryError("recovery_replay_completeness_snapshot_drift")
        return {"status": "passed", "payload": dict(payload), "signature": signature}

    def handle(self, action: ExecutionRecoveryAction, context: Mapping[str, Any]) -> Mapping[str, Any]:
        self._authorize(context, action)
        existing = self._existing(action.action_id)
        action_digest = request_fingerprint(action.to_mapping())
        if existing is not None:
            recovery_evidence = self.verify_recovery_evidence(action.action_id)
            replay_evidence = self.audit_replay_outcome(action)
            if not os.path.exists(self._replay_snapshot_path(action.action_id)):
                raise ExecutionRecoveryError("recovery_replay_snapshot_missing")
            replay_snapshot = self.verify_replay_outcome_snapshot(action)
            replay_inventory_snapshot = self.verify_replay_snapshot_inventory_snapshot(action)
            replay_catalog = self.audit_replay_evidence_catalog()
            replay_catalog_snapshot = self.verify_replay_evidence_catalog_snapshot()
            replay_commit_manifest = self.verify_replay_evidence_commit_manifest(action)
            replay_completeness = self.audit_replay_evidence_completeness(require_durable_snapshot=True)
            replay_completeness_snapshot = self.verify_replay_evidence_completeness_snapshot()
            return {"status": "replayed", "result": existing, "recovery_evidence": recovery_evidence, "replay_evidence": replay_evidence, "replay_snapshot": replay_snapshot, "replay_inventory_snapshot": replay_inventory_snapshot, "replay_catalog": replay_catalog, "replay_catalog_snapshot": replay_catalog_snapshot, "replay_commit_manifest": replay_commit_manifest, "replay_completeness": replay_completeness, "replay_completeness_snapshot": replay_completeness_snapshot}
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
        self.persist_recovery_evidence_status(action.action_id)
        self.persist_replay_outcome_snapshot(action)
        self.persist_replay_snapshot_inventory(action)
        self.persist_replay_evidence_catalog()
        self.persist_replay_evidence_commit_manifest(action)
        self.persist_replay_evidence_completeness()
        self.persist_replay_evidence_commit_manifest(action)
        return payload


__all__ = ["RECOVERY_ACTION_SCHEMA", "ExecutionRecoveryAction", "ExecutionRecoveryError", "ExecutionRecoveryExecutor", "_completion_event_digest"]
      
