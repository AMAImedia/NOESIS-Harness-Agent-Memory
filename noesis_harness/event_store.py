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
        self._seq = 0
        self._load_seen()

    def _load_seen(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            max_seq = 0
            with open(self.path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    self._seen.add(rec.get("event_id", ""))
                    seq = rec.get("seq")
                    if isinstance(seq, int) and seq > max_seq:
                        max_seq = seq
            self._seq = max_seq
        except Exception:
            # Corrupt tail line is tolerated: we just lose its idempotency guard.
            pass

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
                return ident
            self._seq += 1
            rec = {"event_id": ident, "type": event_type, "payload": payload, "seq": self._seq}
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
            self._seen.add(ident)
            return ident

    def iter_events(self) -> Iterable[Dict[str, Any]]:
        """Yield every event in append order."""
        if not os.path.exists(self.path):
            return
        with open(self.path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    yield json.loads(line)

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
