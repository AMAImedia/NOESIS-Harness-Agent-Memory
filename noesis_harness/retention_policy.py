"""noesis_harness/retention_policy.py

Read-only retention policy evaluator for append-only event logs.

Patterns adapted from:
  - LoopX (event_sourced_state.py: append-only log + replay; retention runs as a
    pure projection, never mutating the source-of-truth log)

Design goals:
  - Pure / read-only: evaluate() never writes, moves, or deletes. It only reads
    the event log via EventStore.iter_events() and reports which seq numbers are
    expired under the supplied policy. Enforcement (deletion, archival, compaction)
    is a separate, auditable step.
  - Deterministic: same events_path + policy always yields the same result.
  - Stdlib only: json, os, time. No LLM, no network, no autoloop.

Policy contract
---------------
policy = {
    "max_age_sec": int,            # events older than this (relative to now) are expired
    "keep_types":  [str, ...],      # event `type` values that are NEVER expired
}

An event is expired when ALL of the following hold:
  - its age (now - ts) > max_age_sec, AND
  - its `type` is not in keep_types, AND
  - it carries a parseable timestamp.

Timestamp resolution
--------------------
An event may carry an epoch-second timestamp at the top level (ev["ts"]) or inside
its payload (ev["payload"]["ts"]). Events without a timestamp are treated as
age-unknown and are always retained (conservative: never expire what we cannot date).
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Iterable, List, Optional

from .event_store import EventStore


def _event_timestamp(event: Dict[str, Any]) -> Optional[float]:
    """Return the event's epoch-second timestamp, or None if undatable."""
    ts = event.get("ts")
    if isinstance(ts, (int, float)):
        return float(ts)
    payload = event.get("payload")
    if isinstance(payload, dict):
        pts = payload.get("ts")
        if isinstance(pts, (int, float)):
            return float(pts)
    return None


def evaluate(events_path: str, policy: Dict[str, Any], now: Optional[float] = None) -> Dict[str, Any]:
    """Evaluate a retention policy against an event log, read-only.

    Args:
        events_path: path to the JSONL event log read via EventStore.iter_events().
        policy: dict with keys `max_age_sec` (int) and `keep_types` (list[str]).
        now: optional epoch seconds used as "current time" (for determinism/testing).
             When None, time.time() is used.

    Returns:
        {
            "expired": [seq, ...],   # seq numbers that violate the policy
            "retained_count": int,    # events that satisfy the policy
            "compliant": bool,        # True when no events are expired
        }

    A missing/unreadable events_path is treated as an empty log (compliant: True,
    retained_count: 0, expired: []). This keeps the evaluator read-only and safe:
    a deletion of the log does not fabricate "everything expired" decisions.
    """
    max_age_sec = policy.get("max_age_sec")
    keep_types = set(policy.get("keep_types") or [])

    if not isinstance(max_age_sec, (int, float)) or max_age_sec < 0:
        raise ValueError("policy['max_age_sec'] must be a non-negative number")

    if not os.path.exists(events_path):
        return {"expired": [], "retained_count": 0, "compliant": True}

    current = time.time() if now is None else float(now)

    store = EventStore(events_path)
    expired: List[int] = []
    retained = 0

    for event in store.iter_events():
        etype = event.get("type")
        seq = event.get("seq")
        if etype in keep_types:
            retained += 1
            continue
        ts = _event_timestamp(event)
        if ts is None:
            # Age-unknown events are never expired (conservative, read-only).
            retained += 1
            continue
        age = current - ts
        if max_age_sec == 0:
            # max_age_sec == 0: any dated, non-kept event is immediately expired.
            if age > 0:
                if isinstance(seq, int):
                    expired.append(seq)
                else:
                    retained += 1
            else:
                retained += 1
            continue
        if age > max_age_sec:
            if isinstance(seq, int):
                expired.append(seq)
            else:
                retained += 1
        else:
            retained += 1

    expired.sort()
    return {
        "expired": expired,
        "retained_count": retained,
        "compliant": len(expired) == 0,
    }


def _events_to_records(events: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Helper used by tests to materialize iterables deterministically."""
    return list(events)
