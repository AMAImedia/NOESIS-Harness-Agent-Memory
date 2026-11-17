"""noesis_harness/learning_journal.py

Append-only learning/promotion journal with deterministic replay.

This module is a complementary, side-effect-light companion to
``learning_promotion.py``. Where ``learning_promotion`` runs the governed
promotion state machine, this journal records the *decisions* as an immutable
log so they can be audited and held out against the promotion pipeline.

Borrowed patterns (provenance):
  - LoopX (event_sourced_state.py: AppendOnlyStateEventStore) -- event-sourced,
    append-only log where current truth is always a replay projection, never a
    mutable store.
  - agentmemory (leases.py: TTL leases + idempotent fingerprint writes) -- a
    write is identified by an id plus a content fingerprint so a double-send is
    absorbed, not duplicated.
  - Hermes snapshot discipline (snapshot.py: export_snapshot is read-only and
    reproducible) -- every read here is a pure projection over the log and never
    mutates stored state.

Design guarantees (AGENTS.md HARD rules):
  - stdlib only (hashlib, json, os, threading, time). No external deps.
  - Append-only: writes only ever add lines; the log is never rewritten.
  - Idempotent: the same entry_id + content fingerprint is never written twice.
  - Deterministic: replay() and holdout_summary() are pure functions of the log.
  - Python 3.9+ syntax only (no ``X | None``, no ``match``).

The journal is a *governance record*. It is not a model-generated learning
claim; a promotion is only "governed" when it is recorded here AND verifiable
through the holdout gate in ``learning_promotion``.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from typing import Any, Dict, List, Optional


def _canonical(value: Any) -> str:
    """Deterministic JSON serialization (sorted keys, no whitespace)."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fingerprint(scope: str, action: str, payload: Any) -> str:
    """Stable content hash of a single decision (scope + action + payload)."""
    canon = _canonical({"scope": scope, "action": action, "payload": payload})
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


class LearningJournalConflict(RuntimeError):
    """An entry_id was reused with content that does not match its fingerprint."""


class LearningJournal:
    """Append-only JSONL store for learning/promotion decision events.

    Each line is a JSON object with fields:
      - entry_id    : stable identifier (caller-supplied or content-derived)
      - scope       : governance scope (e.g. ``project:demo``)
      - action      : decision action (e.g. ``record``, ``promote``, ``reject``)
      - payload     : arbitrary JSON-serializable decision detail
      - ts          : epoch seconds at append time (time.time)
      - fingerprint : sha256 over (scope, action, payload)

    Reads are pure projections (replay / holdout_summary). Writes only append.
    """

    def __init__(self, store_path: str) -> None:
        if not store_path:
            raise ValueError("learning_journal_path_required")
        self.path = os.path.abspath(os.path.expanduser(store_path))
        self._lock = threading.Lock()
        self._seen: Dict[str, str] = {}  # entry_id -> fingerprint (idempotency)
        self._load_seen()

    def _read_records(self, repair_tail: bool = False) -> List[Dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "rb") as source:
            raw_lines = source.read().splitlines(keepends=True)
        valid_offset = 0
        records: List[Dict[str, Any]] = []
        for index, raw_line in enumerate(raw_lines):
            if not raw_line.strip():
                valid_offset += len(raw_line)
                continue
            try:
                record = json.loads(raw_line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
                if index == len(raw_lines) - 1 and repair_tail:
                    with open(self.path, "r+b") as fh:
                        fh.truncate(valid_offset)
                    break
                raise
            if not isinstance(record, dict):
                raise ValueError("learning_journal_record_must_be_object")
            records.append(record)
            valid_offset += len(raw_line)
        return records

    def _load_seen(self) -> None:
        for record in self._read_records(repair_tail=True):
            entry_id = str(record.get("entry_id", ""))
            fp = str(record.get("fingerprint", ""))
            prior = self._seen.get(entry_id)
            if prior is not None and prior != fp:
                raise LearningJournalConflict("entry_id reused with different content")
            self._seen[entry_id] = fp

    def record(self, scope: str, action: str, payload: Any, entry_id: Optional[str] = None) -> str:
        """Append a decision event. Idempotent on (entry_id + fingerprint).

        Returns the entry_id. If ``entry_id`` is None, a deterministic id is
        derived from the content fingerprint. A repeat with the same entry_id
        and matching fingerprint is a no-op that returns the prior id.
        """
        if not isinstance(scope, str) or not scope:
            raise ValueError("invalid_scope")
        if not isinstance(action, str) or not action:
            raise ValueError("invalid_action")
        try:
            _canonical(payload)
        except (TypeError, ValueError):
            raise ValueError("payload_not_json_serializable")
        fingerprint = _fingerprint(scope, action, payload)
        ident = entry_id or fingerprint
        with self._lock:
            prior_fp = self._seen.get(ident)
            if prior_fp is not None:
                if prior_fp != fingerprint:
                    raise LearningJournalConflict("entry_id reused with different content")
                return ident
            entry = {
                "entry_id": ident,
                "scope": scope,
                "action": action,
                "payload": payload,
                "ts": time.time(),
                "fingerprint": fingerprint,
            }
            parent = os.path.dirname(self.path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
            self._seen[ident] = fingerprint
            return ident

    def replay(self) -> List[Dict[str, Any]]:
        """Return all entries in append order. Pure projection; never mutates."""
        return self._read_records(repair_tail=True)

    def holdout_summary(self) -> Dict[str, Any]:
        """Deterministic aggregate proving governed, verifiable recording.

        Returns:
          - total            : entry count
          - counts           : per-action counts (sorted keys)
          - earliest_ts      : minimum ts (or 0.0 if empty)
          - latest_ts        : maximum ts (or 0.0 if empty)
          - replay_digest    : stable sha256 over the canonical replay

        The ``replay_digest`` makes the summary reproducible: the same log always
        yields the same digest, so a promotion gate can re-verify it.
        """
        entries = self.replay()
        counts: Dict[str, int] = {}
        earliest: float = 0.0
        latest: float = 0.0
        for index, entry in enumerate(entries):
            action = str(entry.get("action", ""))
            counts[action] = counts.get(action, 0) + 1
            ts = float(entry.get("ts", 0.0))
            if index == 0:
                earliest = ts
                latest = ts
            else:
                if ts < earliest:
                    earliest = ts
                if ts > latest:
                    latest = ts
        replay_digest = hashlib.sha256(_canonical(entries).encode("utf-8")).hexdigest()
        return {
            "total": len(entries),
            "counts": dict(sorted(counts.items())),
            "earliest_ts": earliest,
            "latest_ts": latest,
            "replay_digest": replay_digest,
        }


__all__ = ["LearningJournal", "LearningJournalConflict"]
