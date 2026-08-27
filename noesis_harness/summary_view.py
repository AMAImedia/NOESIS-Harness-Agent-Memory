"""noesis_harness/summary_view.py

Read-only summary projection over the append-only event log.

Patterns adapted from:
  - LoopX (event_sourced_state.py: build_state_projection) -- a read-only
    projection over an event-sourced log that never mutates the log and is
    fully reproducible from the underlying events.
  - agentmemory (summary.py: conversation summarization) -- deriving a compact
    aggregate view from a stream of records without altering the source.

This module is PURE and READ-ONLY. It opens the event log only through
EventStore.iter_events and never writes, repairs, or truncates anything. It
depends solely on the Python standard library (hashlib, json, os) so it stays
dependency-free and importable from any path in the harness.

The public entry point is summarize(events_path), which returns a small,
deterministic dict describing the contents of the log:

    {
        "total": int,                       # number of events
        "per_type": {str: int},             # count per event type
        "top_types": [(str, int), ...],     # per_type ordered by count desc
        "first_seq": int | None,            # lowest seq, or None if empty
        "last_seq": int | None,             # highest seq, or None if empty
        "digest": str,                      # stable SHA-256 of the log content
    }
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from .event_store import EventStore


def _canonical_record(record: Dict[str, Any]) -> str:
    """Return a stable canonical JSON string for a single event record."""
    return json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def _compute_digest(records: List[Dict[str, Any]]) -> str:
    """Return a stable SHA-256 hex digest over the full ordered event log.

    Each record is canonicalized independently (sorted keys) and concatenated
    in append order, so the digest is reproducible for identical log content
    regardless of Python version, platform, or dict key order in the source.
    """
    hasher = hashlib.sha256()
    for record in records:
        hasher.update(_canonical_record(record).encode("utf-8"))
        hasher.update(b"\n")
    return hasher.hexdigest()


def summarize(events_path: str) -> Dict[str, Any]:
    """Build a read-only summary projection over the event log at ``events_path``.

    The function is side-effect free: it never creates, modifies, repairs, or
    deletes the log file. A missing or empty log yields a valid, well-formed
    summary with ``total == 0`` and ``None`` sequence bounds.

    Args:
        events_path: Filesystem path to the append-only JSONL event log.

    Returns:
        A dict with keys: total, per_type, top_types, first_seq, last_seq,
        digest. See module docstring for semantics.
    """
    if not os.path.exists(events_path):
        return {
            "total": 0,
            "per_type": {},
            "top_types": [],
            "first_seq": None,
            "last_seq": None,
            "digest": _compute_digest([]),
        }

    store = EventStore(events_path)
    records = list(store.iter_events())

    total = len(records)
    per_type: Dict[str, int] = {}
    seqs: List[int] = []
    for record in records:
        event_type = str(record.get("type", ""))
        per_type[event_type] = per_type.get(event_type, 0) + 1
        seq = record.get("seq")
        if isinstance(seq, int):
            seqs.append(seq)

    top_types: List[Tuple[str, int]] = sorted(
        per_type.items(), key=lambda item: (-item[1], item[0])
    )

    first_seq: Optional[int] = min(seqs) if seqs else None
    last_seq: Optional[int] = max(seqs) if seqs else None

    return {
        "total": total,
        "per_type": per_type,
        "top_types": top_types,
        "first_seq": first_seq,
        "last_seq": last_seq,
        "digest": _compute_digest(records),
    }


__all__ = ["summarize"]
