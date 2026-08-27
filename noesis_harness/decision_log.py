"""noesis_harness/decision_log.py

Append-only decision records with deterministic replay projection.

Patterns adapted from:
  - LoopX (event_sourced_state.py: append-only event sourcing, idempotent
    double-send absorption)
  - agentmemory (append-only memory records, content-addressable ids)

Design goals:
  - Immutable log: a decision is recorded once and never edited. Any new fact
    is a new record, not a mutation of an old one.
  - Idempotent writes: the same entry_id OR the same content fingerprint never
    appends twice. A double-send is a no-op, not a duplicate.
  - Replayable: current state is always a fold over the JSONL log, so it can be
    rebuilt for audit/debug from the file alone.
  - Scope-aware: decisions can be namespaced (e.g. per agent, per task) so the
    latest() of one scope is independent of another.

Zero dependencies (stdlib only). One file, one job.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from typing import Any, Dict, List, Optional


def _fingerprint(decision: str, rationale: str, actor: Optional[str]) -> str:
    """Stable content hash of a decision record (sha256, canonical JSON)."""
    payload = {
        "decision": decision,
        "rationale": rationale,
        "actor": actor,
    }
    canon = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


class DecisionLogConflict(RuntimeError):
    """An entry ID was reused with different immutable content."""


class DecisionLog:
    """Append-only JSONL decision log with deterministic replay.

    Each line is:
      {"entry_id": str, "decision": str, "rationale": str,
       "actor": str|null, "fingerprint": str, "seq": int}

    The records are always read back in append order; nothing is mutated in
    place. Idempotency keys are (entry_id) and content fingerprint, so a
    repeated call with the same id+fingerprint is absorbed.
    """

    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        self._seen: set = set()            # entry_id -> already appended
        self._fingerprints: Dict[str, str] = {}
        self._seq = 0
        self._load_seen()

    def _read_records(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        records: List[Dict[str, Any]] = []
        with open(self.path, "r", encoding="utf-8") as fh:
            for raw_line in fh:
                if not raw_line.strip():
                    continue
                try:
                    record = json.loads(raw_line)
                except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
                    continue
                if isinstance(record, dict):
                    records.append(record)
        return records

    def _load_seen(self) -> None:
        max_seq = 0
        for record in self._read_records():
            entry_id = str(record.get("entry_id", ""))
            fp = str(record.get("fingerprint", ""))
            prior = self._fingerprints.get(entry_id)
            if prior is not None and prior != fp:
                raise DecisionLogConflict("entry ID reused with different content")
            self._seen.add(entry_id)
            self._fingerprints[entry_id] = fp
            seq = record.get("seq")
            if isinstance(seq, int) and seq > max_seq:
                max_seq = seq
        self._seq = max_seq

    def record(
        self,
        decision: str,
        rationale: str,
        actor: Optional[str] = None,
        entry_id: Optional[str] = None,
    ) -> str:
        """Append one decision record. Idempotent on (entry_id OR fingerprint).

        Returns the entry_id used. If an identical record (same id + fingerprint)
        already exists, the prior id is returned and nothing new is written.
        """
        fingerprint = _fingerprint(decision, rationale, actor)
        with self._lock:
            ident = entry_id or fingerprint
            if ident in self._seen:
                if self._fingerprints.get(ident) != fingerprint:
                    raise DecisionLogConflict("entry ID reused with different content")
                return ident
            self._seq += 1
            rec = {
                "entry_id": ident,
                "decision": decision,
                "rationale": rationale,
                "actor": actor,
                "fingerprint": fingerprint,
                "seq": self._seq,
            }
            parent = os.path.dirname(self.path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
            self._seen.add(ident)
            self._fingerprints[ident] = fingerprint
            return ident

    def replay(self, scope: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return every record in append order.

        If scope is given, only records whose actor equals scope are returned.
        The returned data is a fresh copy; mutating it never touches the log.
        """
        records = self._read_records()
        if scope is not None:
            records = [r for r in records if r.get("actor") == scope]
        return [dict(r) for r in records]

    def latest(self, scope: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Return the most recent record (within scope), or None if empty."""
        records = self.replay(scope=scope)
        if not records:
            return None
        return records[-1]
