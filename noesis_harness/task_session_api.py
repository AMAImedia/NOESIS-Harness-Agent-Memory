"""Versioned task/session command API for the NOESIS execution layer.

The API is intentionally provider- and UI-neutral. It persists commands as
append-only events, validates transitions, supports idempotent retries and
never stores obvious credential material in session text.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Optional

from .event_store import EventStore

SCHEMA_VERSION = "noesis.task-session.v1"

SESSION_STATES = frozenset({"open", "paused", "completed", "cancelled"})
TASK_STATES = frozenset({
    "created", "planned", "waiting_approval", "executing", "review",
    "committed", "rolled_back", "failed", "cancelled",
})

_ALLOWED_TASK_TRANSITIONS = {
    "created": frozenset({"planned", "cancelled"}),
    "planned": frozenset({"waiting_approval", "executing", "cancelled"}),
    "waiting_approval": frozenset({"executing", "cancelled"}),
    "executing": frozenset({"review", "failed", "cancelled"}),
    "review": frozenset({"committed", "rolled_back", "executing", "cancelled"}),
    "committed": frozenset(),
    "rolled_back": frozenset({"planned", "cancelled"}),
    "failed": frozenset({"planned", "cancelled"}),
    "cancelled": frozenset(),
}

_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(?:api[_-]?key|token|password|secret)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"\b(?:sk|hf|ghp|github_pat)_[A-Za-z0-9_\-]{12,}\b"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{12,}"),
)


def _redact_text(value: str) -> str:
    result = str(value)
    for pattern in _SECRET_PATTERNS:
        result = pattern.sub("[REDACTED]", result)
    return result


def _safe_payload(value: Any) -> Any:
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, Mapping):
        return {str(k): _safe_payload(v) for k, v in value.items() if str(k).lower() not in {"api_key", "apikey", "access_token", "refresh_token", "password", "secret"}}
    if isinstance(value, (list, tuple)):
        return [_safe_payload(item) for item in value]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return _redact_text(repr(value))


def _id(prefix: str, seed: str = "") -> str:
    raw = (seed or uuid.uuid4().hex).encode("utf-8")
    return "%s_%s" % (prefix, hashlib.sha256(raw).hexdigest()[:20])


@dataclass(frozen=True)
class SessionRecord:
    session_id: str
    state: str
    created_at: float
    updated_at: float
    owner: str


@dataclass(frozen=True)
class TaskRecord:
    task_id: str
    session_id: str
    state: str
    title: str
    owner: str
    parent_task_id: Optional[str]
    updated_at: float
    reason: str


class TaskSessionError(ValueError):
    """Raised for invalid commands or state transitions."""


class TaskSessionStore:
    """Append-only versioned task/session command store."""

    def __init__(self, event_path: str):
        self.events = EventStore(event_path)

    def _records(self) -> tuple[Dict[str, Any], ...]:
        return tuple(self.events.iter_events() or ())

    def _project(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        state: Dict[str, Dict[str, Dict[str, Any]]] = {"sessions": {}, "tasks": {}}
        for event in self._records():
            payload = event.get("payload") or {}
            kind = event.get("type")
            if kind == "session_created":
                state["sessions"][payload["session_id"]] = dict(payload)
            elif kind == "session_state_changed":
                record = state["sessions"].get(payload["session_id"])
                if record:
                    record["state"] = payload["state"]
                    record["updated_at"] = payload["updated_at"]
            elif kind == "task_created":
                state["tasks"][payload["task_id"]] = dict(payload)
            elif kind == "task_state_changed":
                record = state["tasks"].get(payload["task_id"])
                if record:
                    record["state"] = payload["state"]
                    record["updated_at"] = payload["updated_at"]
                    record["reason"] = payload.get("reason", "")
        return state

    def _append(self, event_type: str, payload: Mapping[str, Any], command_id: Optional[str]) -> str:
        safe = _safe_payload(dict(payload))
        safe["schema_version"] = SCHEMA_VERSION
        safe["command_id"] = command_id or uuid.uuid4().hex
        return self.events.append(event_type, safe, event_id="cmd_" + safe["command_id"])

    def create_session(self, owner: str, session_id: Optional[str] = None, command_id: Optional[str] = None) -> SessionRecord:
        owner = _redact_text(owner).strip()
        if not owner:
            raise TaskSessionError("owner is required")
        sid = session_id or _id("sess")
        now = time.time()
        self._append("session_created", {"session_id": sid, "owner": owner, "state": "open", "created_at": now, "updated_at": now}, command_id or "create-session-" + sid)
        return self.session(sid)

    def create_task(self, session_id: str, title: str, owner: str, parent_task_id: Optional[str] = None, task_id: Optional[str] = None, command_id: Optional[str] = None) -> TaskRecord:
        state = self._project()
        if session_id not in state["sessions"]:
            raise TaskSessionError("unknown session")
        title = _redact_text(title).strip()
        owner = _redact_text(owner).strip()
        if not title or not owner:
            raise TaskSessionError("title and owner are required")
        tid = task_id or _id("task")
        now = time.time()
        self._append("task_created", {"task_id": tid, "session_id": session_id, "state": "created", "title": title, "owner": owner, "parent_task_id": parent_task_id, "updated_at": now, "reason": "created"}, command_id or "create-task-" + tid)
        return self.task(tid)

    def transition_task(self, task_id: str, target: str, reason: str = "", command_id: Optional[str] = None) -> TaskRecord:
        state = self._project()
        record = state["tasks"].get(task_id)
        if not record:
            raise TaskSessionError("unknown task")
        if target not in TASK_STATES:
            raise TaskSessionError("unknown task state")
        current = record["state"]
        if target not in _ALLOWED_TASK_TRANSITIONS[current]:
            raise TaskSessionError("invalid transition %s -> %s" % (current, target))
        now = time.time()
        self._append("task_state_changed", {"task_id": task_id, "session_id": record["session_id"], "from": current, "state": target, "reason": reason, "updated_at": now}, command_id or "transition-%s-%s" % (task_id, target))
        return self.task(task_id)

    def append_message(self, session_id: str, role: str, content: str, command_id: Optional[str] = None) -> str:
        if session_id not in self._project()["sessions"]:
            raise TaskSessionError("unknown session")
        if role not in {"system", "user", "assistant", "tool", "event"}:
            raise TaskSessionError("invalid message role")
        safe = _redact_text(content)
        return self._append("session_message", {"session_id": session_id, "role": role, "content": safe, "created_at": time.time()}, command_id)

    def session(self, session_id: str) -> SessionRecord:
        record = self._project()["sessions"].get(session_id)
        if not record:
            raise TaskSessionError("unknown session")
        return SessionRecord(record["session_id"], record["state"], record["created_at"], record["updated_at"], record["owner"])

    def task(self, task_id: str) -> TaskRecord:
        record = self._project()["tasks"].get(task_id)
        if not record:
            raise TaskSessionError("unknown task")
        return TaskRecord(record["task_id"], record["session_id"], record["state"], record["title"], record["owner"], record.get("parent_task_id"), record["updated_at"], record.get("reason", ""))

    def messages(self, session_id: str) -> tuple[Mapping[str, Any], ...]:
        if session_id not in self._project()["sessions"]:
            raise TaskSessionError("unknown session")
        return tuple(event["payload"] for event in self._records() if event.get("type") == "session_message" and event.get("payload", {}).get("session_id") == session_id)

    def resume(self, session_id: str) -> Mapping[str, Any]:
        session = self.session(session_id)
        tasks = tuple(self.task(tid) for tid, record in self._project()["tasks"].items() if record["session_id"] == session_id)
        return {"schema_version": SCHEMA_VERSION, "session": session, "tasks": tasks, "messages": self.messages(session_id), "event_count": self.events.count()}


__all__ = ["SCHEMA_VERSION", "SessionRecord", "TaskRecord", "TaskSessionError", "TaskSessionStore"]
