"""Durable delegated-task resume and replay guards.

Patterns adapted from deepseek-harness session replay, Hermes durable task
memory, agent-teams work-product ownership, and this project's EventStore.
The module stores only redacted identity metadata and never executes a child.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from .event_store import EventStore

SCHEMA_VERSION = "noesis.delegated-resume.v1"
TERMINAL_STATES = frozenset({"completed", "failed", "cancelled"})
RESUMABLE_STATES = frozenset({"interrupted", "failed"})


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class DelegationIdentity:
    delegation_id: str
    session_id: str
    task_id: str
    agent_id: str
    workspace: str
    capabilities: tuple[str, ...]
    request_digest: str


@dataclass(frozen=True)
class DelegationSnapshot:
    identity: DelegationIdentity
    state: str
    checkpoint: str
    checkpoint_digest: str
    approval_consumed: bool
    updated_at: float


class DelegatedResumeError(ValueError):
    """Raised when a delegated resume or replay guard fails closed."""


class DelegatedResumeStore:
    """Append-only identity, checkpoint and single-use resume approval store."""

    def __init__(self, event_path: str):
        self.events = EventStore(event_path)

    @staticmethod
    def _identity_payload(session_id: str, task_id: str, agent_id: str, workspace: str, capabilities: tuple[str, ...]) -> dict[str, Any]:
        return {"session_id": session_id, "task_id": task_id, "agent_id": agent_id, "workspace": workspace, "capabilities": list(capabilities)}

    def create(self, session_id: str, task_id: str, agent_id: str, workspace: str, capabilities: tuple[str, ...], *, delegation_id: Optional[str] = None) -> DelegationIdentity:
        if not all(str(value).strip() for value in (session_id, task_id, agent_id, workspace)):
            raise DelegatedResumeError("delegation_identity_required")
        normalized = tuple(sorted({str(item).strip() for item in capabilities if str(item).strip()}))
        if not normalized:
            raise DelegatedResumeError("delegation_capabilities_required")
        payload = self._identity_payload(str(session_id), str(task_id), str(agent_id), str(workspace), normalized)
        did = delegation_id or "delegation_" + uuid.uuid4().hex
        existing = self._record(did)
        if existing is not None:
            if existing["request_digest"] != _digest(payload):
                raise DelegatedResumeError("delegation_identity_immutable")
            return self.identity(did)
        self.events.append("delegation_created", {"schema_version": SCHEMA_VERSION, "delegation_id": did, **payload, "request_digest": _digest(payload), "state": "created", "checkpoint": "", "checkpoint_digest": "", "updated_at": time.time()}, event_id="delegation-created-" + did)
        return self.identity(did)

    def checkpoint(self, delegation_id: str, checkpoint: str) -> DelegationSnapshot:
        record = self._record(delegation_id)
        if record is None:
            raise DelegatedResumeError("unknown_delegation")
        if record["state"] in TERMINAL_STATES:
            raise DelegatedResumeError("terminal_delegation_not_checkpointable")
        text = str(checkpoint)
        digest = _digest({"delegation_id": delegation_id, "checkpoint": text})
        self.events.append("delegation_checkpointed", {"delegation_id": delegation_id, "checkpoint": text, "checkpoint_digest": digest, "state": "checkpointed", "updated_at": time.time()}, event_id="checkpoint-" + delegation_id + "-" + digest)
        return self.snapshot(delegation_id)

    def mark_interrupted(self, delegation_id: str, reason: str = "child_interrupted") -> DelegationSnapshot:
        return self._state(delegation_id, "interrupted", reason)

    def approve_resume(self, delegation_id: str, approval_token: str) -> str:
        record = self._record(delegation_id)
        if record is None:
            raise DelegatedResumeError("unknown_delegation")
        if record["state"] not in RESUMABLE_STATES:
            raise DelegatedResumeError("fresh_resume_approval_required_after_interruption")
        token = str(approval_token)
        if not token:
            raise DelegatedResumeError("resume_approval_required")
        approval_id = "resume_approval_" + _digest({"delegation_id": delegation_id, "token": token, "checkpoint_digest": record.get("checkpoint_digest", "")})[:24]
        self.events.append("delegation_resume_approved", {"delegation_id": delegation_id, "approval_id": approval_id, "approval_digest": _digest(token), "checkpoint_digest": record.get("checkpoint_digest", ""), "state": "resume_approved", "updated_at": time.time()}, event_id="resume-approval-" + approval_id)
        return approval_id

    def consume_resume_approval(self, delegation_id: str, approval_id: str, *, request_digest: str) -> DelegationSnapshot:
        record = self._record(delegation_id)
        if record is None:
            raise DelegatedResumeError("unknown_delegation")
        if record.get("request_digest") != request_digest:
            raise DelegatedResumeError("delegation_request_mutated")
        approvals = [event.get("payload", {}) for event in self.events.iter_events() if event.get("type") == "delegation_resume_approved" and event.get("payload", {}).get("delegation_id") == delegation_id and event.get("payload", {}).get("approval_id") == approval_id]
        if not approvals:
            raise DelegatedResumeError("resume_approval_not_found")
        consumed = [event for event in self.events.iter_events() if event.get("type") == "delegation_resume_consumed" and event.get("payload", {}).get("approval_id") == approval_id]
        if consumed:
            raise DelegatedResumeError("resume_approval_replayed")
        approval = approvals[-1]
        if approval.get("checkpoint_digest") != record.get("checkpoint_digest", ""):
            raise DelegatedResumeError("resume_checkpoint_drift")
        self.events.append("delegation_resume_consumed", {"delegation_id": delegation_id, "approval_id": approval_id, "request_digest": request_digest, "state": "resuming", "updated_at": time.time()}, event_id="resume-consumed-" + approval_id)
        return self.snapshot(delegation_id)

    def complete(self, delegation_id: str, state: str = "completed") -> DelegationSnapshot:
        if state not in TERMINAL_STATES:
            raise DelegatedResumeError("invalid_terminal_state")
        return self._state(delegation_id, state, "delegation_terminal")

    def _state(self, delegation_id: str, state: str, reason: str) -> DelegationSnapshot:
        if self._record(delegation_id) is None:
            raise DelegatedResumeError("unknown_delegation")
        self.events.append("delegation_state_changed", {"delegation_id": delegation_id, "state": state, "reason": reason, "updated_at": time.time()}, event_id="state-" + delegation_id + "-" + state + "-" + uuid.uuid4().hex)
        return self.snapshot(delegation_id)

    def _record(self, delegation_id: str) -> Optional[dict[str, Any]]:
        record: Optional[dict[str, Any]] = None
        for event in self.events.iter_events():
            payload = event.get("payload") or {}
            if payload.get("delegation_id") != delegation_id:
                continue
            if event.get("type") == "delegation_created":
                record = dict(payload)
            elif record is not None and event.get("type") == "delegation_checkpointed":
                record.update({"checkpoint": payload.get("checkpoint", ""), "checkpoint_digest": payload.get("checkpoint_digest", ""), "state": payload.get("state", "checkpointed")})
            elif record is not None and event.get("type") in {"delegation_state_changed", "delegation_resume_approved", "delegation_resume_consumed"}:
                record.update({"state": payload.get("state", record.get("state")), "updated_at": payload.get("updated_at", record.get("updated_at"))})
        return record

    def identity(self, delegation_id: str) -> DelegationIdentity:
        record = self._record(delegation_id)
        if record is None:
            raise DelegatedResumeError("unknown_delegation")
        return DelegationIdentity(delegation_id, record["session_id"], record["task_id"], record["agent_id"], record["workspace"], tuple(record["capabilities"]), record["request_digest"])

    def snapshot(self, delegation_id: str) -> DelegationSnapshot:
        record = self._record(delegation_id)
        if record is None:
            raise DelegatedResumeError("unknown_delegation")
        consumed = any(event.get("type") == "delegation_resume_consumed" and event.get("payload", {}).get("delegation_id") == delegation_id for event in self.events.iter_events())
        return DelegationSnapshot(self.identity(delegation_id), str(record.get("state", "created")), str(record.get("checkpoint", "")), str(record.get("checkpoint_digest", "")), consumed, float(record.get("updated_at", 0.0)))


__all__ = ["SCHEMA_VERSION", "DelegationIdentity", "DelegationSnapshot", "DelegatedResumeError", "DelegatedResumeStore"]
