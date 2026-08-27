"""noesis_harness/keyword_index.py

Local, deterministic, read-only inverted keyword index over the append-only
event log.

Patterns adapted from:
  - agentmemory  (deterministic term-overlap retrieval, no embeddings)
  - LoopX        (replay projection: derive a read-only view by folding events)

This module builds a pure inverted index (term -> [event_ids]) from the JSONL
event log. It is fully offline: no LLM call, no external search backend, no
write to the log. Given a path to the event log it tokenizes each event payload
and maps every term to the list of event ids that contain it.

Design guarantees (see AGENTS.md):
  - Append-only safe: opens the log read-only; never mutates it.
  - Deterministic: pure/stateless; identical inputs -> identical index.
  - Idempotent: building the index has no side effects.
  - Immutable result: callers receive copies; mutating them does not change the
    index, and search() returns a fresh copy each call.
  - Python 3.9+ syntax: no `X | None`, no `match`.

Zero dependencies (stdlib only): json, os, re.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List

_TOKEN_RE = re.compile(r"[a-z0-9_]+")


def _tokenize(text: str) -> set:
    """Lowercase word/number token set for deterministic term overlap."""
    return set(_TOKEN_RE.findall(text.lower()))


def _serialize_payload(payload: Any) -> str:
    """Stable JSON serialization of an event payload for text matching."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)


def _read_events(events_path: str) -> List[Dict[str, Any]]:
    """Read every event from a JSONL log in append order (read-only).

    Tolerates a missing log (returns []), a non-file path, and blank or
    unparseable trailing lines. Never writes to the log.
    """
    if not events_path or not os.path.isfile(events_path):
        return []
    events: List[Dict[str, Any]] = []
    with open(events_path, "r", encoding="utf-8") as source:
        for raw_line in source:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                record = json.loads(raw_line)
            except (ValueError, json.JSONDecodeError):
                continue
            if isinstance(record, dict):
                events.append(record)
    return events


def build(events_path: str) -> Dict[str, List[str]]:
    """Build a read-only inverted keyword index over the event log.

    Returns a dict mapping each lowercase term to the ordered list of event ids
    whose payload contains that term. Terms are extracted via a deterministic
    tokenizer over the canonical JSON serialization of each event payload.

    Determinism: the same log yields byte-identical indexes. Immutability: the
    returned dict and its lists are fresh copies; mutating them does not affect
    future calls. A missing or empty log yields an empty dict.
    """
    index: Dict[str, List[str]] = {}
    for event in _read_events(events_path):
        event_id = str(event.get("event_id", ""))
        payload_text = _serialize_payload(event.get("payload"))
        for term in _tokenize(payload_text):
            seen = index.get(term)
            if seen is None:
                index[term] = [event_id]
            elif event_id not in seen:
                seen.append(event_id)
    return index


def search(index: Dict[str, List[str]], term: str) -> List[str]:
    """Return the event ids for a term (case-insensitive).

    Looks up an exact term in the index and returns a copy of the ordered event
    id list. Unknown terms return an empty list. The result is a fresh list, so
    callers may mutate it without affecting the index.
    """
    return list(index.get(term.lower(), []))


__all__ = ["build", "search"]
