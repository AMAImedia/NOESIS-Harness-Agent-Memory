"""noesis_harness/event_stream.py — streaming read of event log.

Patterns: LoopX streaming replay.
Stdlib only.
"""
from __future__ import annotations
from typing import Iterator, Dict, Any
from noesis_harness.event_store import EventStore

def stream(events_path: str, batch_size: int = 100) -> Iterator[list]:
    store = EventStore(events_path)
    batch = []
    for rec in store.iter_events():
        batch.append(rec)
        if len(batch) >= batch_size:
            yield batch; batch = []
    if batch: yield batch
