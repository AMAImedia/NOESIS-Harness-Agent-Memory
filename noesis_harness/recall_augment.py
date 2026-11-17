"""noesis_harness/recall_augment.py

Local, deterministic, retrieval-augmented recall over the append-only event log.

Patterns adapted from:
  - LoopX            (replay projection: derive current view by folding events)
  - agentmemory      (deterministic term-overlap retrieval, no embeddings)
  - deepseek-harness (offline context packing for agent prompts)

This module is a safe, stdlib-only extension of the t-search bridge idea. It
works fully offline: no LLM call, no external search backend. Given a query and
an event-log path it produces a ranked, read-only context block.

Design guarantees (see AGENTS.md):
  - Append-only safe: opens the log read-only via EventStore.iter_events().
  - Deterministic: pure/stateless scoring; identical inputs -> identical output.
  - Idempotent: ranking never mutates the log and has no side effects.
  - Python 3.9+ syntax: no `X | None`, no `match`.

Zero dependencies (stdlib only): hashlib, json, math, os, re.
"""

from __future__ import annotations

import json
import math
import os
import re
from typing import Any, Dict, Iterable, List, Optional

from .event_store import EventStore

_TOKEN_RE = re.compile(r"[a-z0-9_]+")

# Weight of the recency bonus relative to the term-overlap component.
RECENCY_WEIGHT = 0.1
# Maximum length (in characters) of a returned snippet.
SNIPPET_LIMIT = 160


def _tokenize(text: str) -> set:
    """Lowercase word/number token set for deterministic term overlap."""
    return set(_TOKEN_RE.findall(text.lower()))


def _serialize_payload(payload: Any) -> str:
    """Stable JSON serialization of an event payload for text matching."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)


def _make_snippet(text: str) -> str:
    """Truncate a payload text into a display-safe snippet."""
    if len(text) <= SNIPPET_LIMIT:
        return text
    return text[:SNIPPET_LIMIT].rstrip() + "..."


def _score_event(query_tokens: set, payload_text: str, seq: int, max_seq: int) -> float:
    """Pure, stateless relevance score: term overlap + recency bonus.

    term overlap is the fraction of query tokens present in the payload text
    (0.0 when the query is empty). recency is seq/max_seq in [0, 1].
    """
    payload_tokens = _tokenize(payload_text)
    if query_tokens:
        hits = sum(1 for token in query_tokens if token in payload_tokens)
        overlap = float(hits) / float(len(query_tokens))
    else:
        overlap = 0.0
    recency = (float(seq) / float(max_seq)) if max_seq > 0 else 0.0
    # Recency only refines among events that actually match the query, so an
    # empty query (no overlap) yields a zero score and no context.
    return overlap + RECENCY_WEIGHT * recency * overlap


def _read_events(events_path: str) -> List[Dict[str, Any]]:
    """Yield every event from the log in append order (read-only)."""
    store = EventStore(events_path)
    return [ev for ev in store.iter_events()]


def rank_events(query: str, events_path: str, top_k: int = 8) -> List[Dict[str, Any]]:
    """Rank events by deterministic relevance and return the top_k.

    Reads the append-only event log via EventStore.iter_events() (read-only),
    scores each event by term overlap between the query and the JSON-serialized
    payload, plus a small recency bonus from `seq`, then returns the top_k
    events as dicts with keys: seq, event_id, type, score, snippet.

    Deterministic given the same inputs. Returns an empty list when the log is
    missing or empty. Never writes to the log.
    """
    query_tokens = _tokenize(query)
    events = _read_events(events_path)
    if not events:
        return []

    max_seq = 0
    for ev in events:
        seq = ev.get("seq")
        if isinstance(seq, int) and seq > max_seq:
            max_seq = seq

    ranked: List[Dict[str, Any]] = []
    for ev in events:
        seq = ev.get("seq") if isinstance(ev.get("seq"), int) else 0
        payload = ev.get("payload")
        payload_text = _serialize_payload(payload)
        score = _score_event(query_tokens, payload_text, int(seq), max_seq)
        ranked.append(
            {
                "seq": int(seq),
                "event_id": str(ev.get("event_id", "")),
                "type": str(ev.get("type", "")),
                "score": score,
                "snippet": _make_snippet(payload_text),
            }
        )

    ranked.sort(key=lambda item: (item["score"], item["seq"]), reverse=True)
    if top_k is not None and top_k >= 0:
        ranked = ranked[:top_k]
    return ranked


def build_augmented_context(query: str, events_path: str, top_k: int = 8) -> str:
    """Build a compact Markdown-ish context block from the top_k events.

    Returns an empty string when no events rank above zero relevance or the log
    is missing/empty. Read-only and side-effect free.
    """
    ranked = rank_events(query, events_path, top_k=top_k)
    if not ranked:
        return ""

    lines: List[str] = ["## Recalled context", ""]
    for index, item in enumerate(ranked, start=1):
        if item["score"] <= 0.0:
            continue
        lines.append(
            "### {0}. [{1}] seq={2} score={3:.4f}".format(
                index, item["type"], item["seq"], item["score"]
            )
        )
        lines.append("")
        lines.append("```")
        lines.append(item["snippet"])
        lines.append("```")
        lines.append("")
    if len(lines) <= 2:
        return ""
    return "\n".join(lines).rstrip() + "\n"


__all__ = ["rank_events", "build_augmented_context"]
