"""noesis_harness/event_aggregator.py — read-only aggregation over events.

Patterns: LoopX projection.
Stdlib only.
"""
from __future__ import annotations
from collections import Counter
from noesis_harness.event_store import EventStore

def aggregate(events_path: str):
    counts = Counter(); total = 0
    for r in EventStore(events_path).iter_events():
        counts[r.get("type", "unknown")] += 1; total += 1
    return {"total": total, "per_type": dict(counts), "top": counts.most_common(3)}
