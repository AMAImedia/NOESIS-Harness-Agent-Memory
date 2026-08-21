"""noesis_harness/event_store.py

Append-only event log with deterministic projection.

Patterns adapted from:
  - LoopX  (event_sourced_state.py: AppendOnlyStateEventStore + build_state_projection)
  - deepseek-harness (Session.append: event-sourced, idempotent)

Design goals:
  - Idempotent append: the same event_id + fingerprint never writes twice.
  - Current state is a REPLAY of events, not a mutable store.
  - Crash-safe: append-only JSONL means a partial write only loses the last line.

Zero dependencies (stdlib only). One file, one job.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from typing import Any, Callable, Dict, Iterable, List, Optional


def _fingerprint(event_type: str, payload: Any) -> str:
    """Stable content hash of an event (type + canonical JSON payload)."""
    canon = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(f"{event_type}\x00{canon}".encode("utf-8")).hexdigest()


class EventStoreCorrupt(RuntimeError):
    """A non-tail event-log record is malformed and cannot be replayed safely."""


class EventStoreConflict(RuntimeError):
    """An event ID was reused with different immutable content."""


class EventStore:
    """Append-only JSONL event log + deterministic replay projection.

    Each line is: {"event_id": str, "type": str, "payload": ..., "seq": int}.
    The projection is built by folding every event through registered reducers,
    so the current state can always be rebuilt from the log (replay/debug/audit).
    """

    def __init__(self, path: str, reducers: Optional[Dict[str, Callable]] = None):
        self.path = path
        self._lock = threading.Lock()
        self._reducers: Dict[str, Callable] = dict(reducers or {})
        self._seen: set = set()       # event_id -> already appended (idempotency)
        self._fingerprints: dict[str, str] = {}
        self._seq = 0
        self._load_seen()

    def _read_records(self, repair_tail: bool = False) -> Iterable[Dict[str, Any]]:
        if not os.path.exists(self.path):
            return
        with open(self.path, "rb") as source:
            raw_lines = source.read().splitlines(keepends=True)
        valid_offset = 0
        for index, raw_line in enumerate(raw_lines):
            if not raw_line.strip():
                valid_offset += len(raw_line)
                continue
            try:
                record = json.loads(raw_line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
                if index == len(raw_lines) - 1:
                    if repair_tail:
                        with open(self.path, "r+b") as fh:
                            fh.truncate(valid_offset)
                    return
                raise EventStoreCorrupt("event log corruption before tail") from exc
            if not isinstance(record, dict):
                raise EventStoreCorrupt("event record must be an object")
            valid_offset += len(raw_line)
            yield record

    def _load_seen(self) -> None:
        max_seq = 0
        for record in self._read_records(repair_tail=True) or ():
            event_id = str(record.get("event_id", ""))
            fingerprint = _fingerprint(str(record.get("type", "")), record.get("payload"))
            prior = self._fingerprints.get(event_id)
            if prior is not None and prior != fingerprint:
                raise EventStoreConflict("event ID reused with different content")
            self._seen.add(event_id)
            self._fingerprints[event_id] = fingerprint
            seq = record.get("seq")
            if isinstance(seq, int) and seq > max_seq:
                max_seq = seq
        self._seq = max_seq

    def register_reducer(self, event_type: str, reducer: Callable) -> None:
        """Register a reducer: (state, payload) -> state for a given event type."""
        self._reducers[event_type] = reducer

    def append(self, event_type: str, payload: Any, event_id: Optional[str] = None) -> str:
        """Append one event. Idempotent on (event_id OR content-fingerprint).

        Returns the event_id. If an identical pending event already exists, the
        prior id is returned and nothing new is written (double-send absorbs here).
        """
        with self._lock:
            ident = event_id or _fingerprint(event_type, payload)
            if ident in self._seen:
                current = _fingerprint(event_type, payload)
                if self._fingerprints.get(ident) != current:
                    raise EventStoreConflict("event ID reused with different content")
                return ident
            self._seq += 1
            rec = {"event_id": ident, "type": event_type, "payload": payload, "seq": self._seq}
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
            self._seen.add(ident)
            self._fingerprints[ident] = _fingerprint(event_type, payload)
            return ident

    def iter_events(self) -> Iterable[Dict[str, Any]]:
        """Yield every event in append order, repairing only a malformed tail."""
        yield from (self._read_records(repair_tail=True) or ())

    def project(self, initial: Any = None) -> Any:
        """Deterministic replay: fold all events through reducers into a state."""
        state = initial
        for ev in self.iter_events():
            reducer = self._reducers.get(ev.get("type"))
            if reducer is not None:
                state = reducer(state, ev.get("payload"))
        return state

    def count(self) -> int:
        return len(self._seen)


def project_chain(reducers: Dict[str, Callable]) -> Callable:
    """Convenience: build a projection function from a reducer map."""
    def run(events: Iterable[Dict[str, Any]], initial: Any = None) -> Any:
        state = initial
        for ev in events:
            r = reducers.get(ev.get("type"))
            if r is not None:
                state = r(state, ev.get("payload"))
        return state
    return run


__all__ = ["EventStore", "EventStoreCorrupt", "EventStoreConflict", "project_chain"]
