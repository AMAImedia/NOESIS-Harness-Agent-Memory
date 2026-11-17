"""Versioned interactive session streaming contract.

This module defines transport-neutral events. HTTP/SSE, terminal rendering and a
future desktop shell can all consume the same bounded event envelopes.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from threading import Event, Lock
from typing import Any, Iterable, Mapping, Optional

STREAM_SCHEMA = "noesis.session-stream.v1"
MAX_EVENT_BYTES = 64 * 1024


class StreamContractError(ValueError):
    """Raised when a stream event violates the bounded contract."""


@dataclass(frozen=True)
class StreamEvent:
    session_id: str
    sequence: int
    kind: str
    data: Mapping[str, Any]
    task_id: Optional[str] = None
    created_at: float = 0.0
    schema_version: str = STREAM_SCHEMA

    def envelope(self) -> dict[str, Any]:
        if not self.session_id or self.sequence < 1 or not self.kind:
            raise StreamContractError("invalid event identity")
        payload = {
            "schema_version": self.schema_version,
            "session_id": self.session_id,
            "sequence": self.sequence,
            "kind": self.kind,
            "task_id": self.task_id,
            "created_at": self.created_at or time.time(),
            "data": dict(self.data),
        }
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        if len(encoded.encode("utf-8")) > MAX_EVENT_BYTES:
            raise StreamContractError("event exceeds bounded payload")
        return payload

    def sse(self) -> str:
        payload = json.dumps(self.envelope(), ensure_ascii=False, separators=(",", ":"))
        return "id: %d\nevent: %s\ndata: %s\n\n" % (self.sequence, self.kind, payload)


class CancellationToken:
    """Thread-safe cancellation primitive shared by provider/tool workers."""

    def __init__(self) -> None:
        self._event = Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self.cancelled:
            raise StreamContractError("session_cancelled")


class SessionEventBuffer:
    """Bounded in-memory stream buffer with Last-Event-ID reconnect support."""

    def __init__(self, session_id: str, max_events: int = 512):
        if not session_id or max_events < 1:
            raise StreamContractError("invalid buffer configuration")
        self.session_id = session_id
        self.max_events = max_events
        self._events: list[StreamEvent] = []
        self._next_sequence = 1
        self._lock = Lock()

    def publish(self, kind: str, data: Mapping[str, Any], task_id: Optional[str] = None) -> StreamEvent:
        with self._lock:
            event = StreamEvent(self.session_id, self._next_sequence, kind, dict(data), task_id=task_id, created_at=time.time())
            event.envelope()
            self._events.append(event)
            self._next_sequence += 1
            if len(self._events) > self.max_events:
                del self._events[: len(self._events) - self.max_events]
            return event

    def since(self, last_event_id: int = 0) -> tuple[StreamEvent, ...]:
        if last_event_id < 0:
            raise StreamContractError("last_event_id must be non-negative")
        with self._lock:
            return tuple(event for event in self._events if event.sequence > last_event_id)

    def sse_since(self, last_event_id: int = 0) -> str:
        return "".join(event.sse() for event in self.since(last_event_id))


__all__ = ["STREAM_SCHEMA", "MAX_EVENT_BYTES", "StreamContractError", "StreamEvent", "CancellationToken", "SessionEventBuffer"]
