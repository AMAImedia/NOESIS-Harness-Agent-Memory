"""noesis_harness/batch_writer.py

Append-only batched writer over EventStore.

Patterns adapted from:
  - LoopX  (event_sourced_state.py: AppendOnlyStateEventStore + batched idempotent append)
  - deepseek-harness (Session.append: event-sourced, idempotent)

Design goals:
  - write_many appends a list of (type, payload) tuples in one call.
  - Idempotent: re-appending the exact same batch is a no-op (content-fingerprint
    keys via EventStore.append).
  - Missing file is created on first append (delegated to EventStore).
  - No LLM, no network, no external dependency. Crash-safe append-only JSONL.

Zero dependencies (stdlib only). One file, one job.
"""

from __future__ import annotations

import os
from typing import Any, List, Optional, Tuple

from .event_store import EventStore, _fingerprint


class BatchWriter:
    """Append-only batched writer over an EventStore.

    A thin convenience layer: it collects (type, payload) pairs and writes them
    through EventStore.append, which guarantees each event is persisted idempotently
    (a double-send with identical content is absorbed). count() reflects the number
    of distinct events currently persisted.
    """

    def __init__(self, path: str):
        self.path = path
        self._store = EventStore(path)

    def write_many(self, events: List[Tuple[str, Any]]) -> List[str]:
        """Append a batch of (type, payload) events idempotently.

        Returns the list of event_ids written (only those that were new; an
        already-persisted event contributes its existing id without a new write).
        An empty list is a no-op.
        """
        written: List[str] = []
        for event_type, payload in events:
            ident = _fingerprint(event_type, payload)
            self._store.append(event_type, payload, event_id=ident)
            written.append(ident)
        return written

    def count(self) -> int:
        """Number of distinct events persisted in the backing store."""
        return self._store.count()

    def exists(self) -> bool:
        """Whether the backing event-log file has been materialized yet."""
        return os.path.exists(self.path)


__all__ = ["BatchWriter"]
