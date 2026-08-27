"""noesis_harness/metrics_snapshot.py

Read-only metrics over an append-only event log.

Patterns adapted from:
  - LoopX  (event_sourced_state.py: build_state_projection — derive stable
             read-only summaries by folding the event log deterministically)

This module NEVER writes. It opens the log through
EventStore.iter_events (which only repairs a malformed tail) and derives a
stable, deterministic snapshot: total counts, per-type counts, the time span
(min/max timestamp if a timestamp is present anywhere in the event), and a
sha256 digest over the canonical summary so two identical logs hash equal.

Zero dependencies (stdlib only). One file, one job.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, List, Optional

from .event_store import EventStore

_TS_KEYS = ("ts", "timestamp", "time")


def _event_ts(event: Dict[str, Any]) -> Optional[Any]:
    """Best-effort timestamp extraction from an event.

    Looks for a timestamp at the event top level, then inside the payload.
    Returns the first non-null value found, else None. The value is returned
    untouched (string or number) so that min/max compare consistently.
    """
    for key in _TS_KEYS:
        if key in event and event[key] is not None:
            return event[key]
    payload = event.get("payload")
    if isinstance(payload, dict):
        for key in _TS_KEYS:
            if key in payload and payload[key] is not None:
                return payload[key]
    return None


def _canonical_summary(total: int, per_type: Dict[str, int],
                       min_ts: Optional[Any], max_ts: Optional[Any],
                       seq_max: int) -> str:
    """Deterministic, order-independent canonical string for the summary."""
    summary = {
        "total": total,
        "per_type": {k: per_type[k] for k in sorted(per_type)},
        "time_span": {"min": min_ts, "max": max_ts},
        "seq_max": seq_max,
    }
    return json.dumps(summary, sort_keys=True, ensure_ascii=False, default=str)


def snapshot(events_path: str) -> Dict[str, Any]:
    """Compute read-only metrics over an event log.

    Args:
        events_path: path to a JSONL event log consumed via EventStore.iter_events.

    Returns a dict with:
        - total: int, total number of events
        - per_type: dict[str, int], count per event type
        - time_span: {"min": ts|None, "max": ts|None}; ts present only if at
          least one event carried a timestamp at top level or in its payload
        - seq_max: int, highest seq seen (0 if none)
        - digest: str, sha256 hex of the canonical summary

    Pure/read-only: this function never appends or mutates the log.
    """
    store = EventStore(events_path)
    total = 0
    per_type: Dict[str, int] = {}
    min_ts: Optional[Any] = None
    max_ts: Optional[Any] = None
    seq_max = 0

    for event in store.iter_events():
        total += 1
        etype = str(event.get("type", ""))
        per_type[etype] = per_type.get(etype, 0) + 1
        ts = _event_ts(event)
        if ts is not None:
            if min_ts is None or ts < min_ts:
                min_ts = ts
            if max_ts is None or ts > max_ts:
                max_ts = ts
        seq = event.get("seq")
        if isinstance(seq, int) and seq > seq_max:
            seq_max = seq

    canonical = _canonical_summary(total, per_type, min_ts, max_ts, seq_max)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    return {
        "total": total,
        "per_type": per_type,
        "time_span": {"min": min_ts, "max": max_ts},
        "seq_max": seq_max,
        "digest": digest,
    }


__all__ = ["snapshot"]
