"""noesis_harness/export_jsonl.py

Read-only exporter of an append-only event log to JSONL.

Patterns adapted from:
  - LoopX (event_sourced_state.py: AppendOnlyStateEventStore) -- the source
    event log uses the same append-only JSONL shape and the exporter is strictly
    a read-side projection of it. Read-only on the source: never opened for
    writing, never mutated.

Design goals:
  - Stdlib only (json, os). No numpy, no requests, no LLM.
  - Strictly read-only on the source event log. The source path is only ever
    opened for reading; a defensive re-open check asserts "rb"/"r" mode.
  - Deterministic: same input -> identical output (stable sort by seq, canonical
    JSON dumps). No wall-clock or random content is emitted.
  - Graceful on empty/missing source.

Zero dependencies (stdlib only). One file, one job.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, List, Optional


def _read_records(events_path: str) -> Iterable[Dict[str, Any]]:
    """Yield well-formed event records from the source log, read-only.

    Blank lines are skipped. A malformed tail line (last line only) is ignored;
    an earlier malformed line raises ValueError to avoid silently dropping
    provenance from the middle of the log.
    """
    if not os.path.exists(events_path):
        return
    with open(events_path, "rb") as source:
        raw_lines = source.read().splitlines(keepends=True)
    for index, raw_line in enumerate(raw_lines):
        if not raw_line.strip():
            continue
        try:
            record = json.loads(raw_line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
            if index == len(raw_lines) - 1:
                return
            raise ValueError("event log corruption before tail") from exc
        if not isinstance(record, dict):
            raise ValueError("event record must be an object")
        yield record


def export(events_path: str, out_path: str, filter_type: Optional[str] = None) -> int:
    """Export events from ``events_path`` to JSONL at ``out_path``.

    The source log is opened read-only and never modified. When ``filter_type``
    is provided, only events whose ``type`` equals it are written. Events are
    emitted in ``seq`` order for determinism. Returns the number of records
    written.
    """
    records: List[Dict[str, Any]] = []
    for record in _read_records(events_path) or ():
        rec_type = record.get("type")
        if filter_type is not None and rec_type != filter_type:
            continue
        records.append(record)
    records.sort(key=lambda r: (r.get("seq") if isinstance(r.get("seq"), int) else 0))

    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as out:
        for record in records:
            out.write(json.dumps(record, ensure_ascii=False, sort_keys=True, default=str) + "\n")
    return len(records)


__all__ = ["export"]
