"""noesis_harness/consent_log.py

Append-only consent records with deterministic fingerprinting and replay.

Patterns adapted from:
  - LoopX (AppendOnlyStateEventStore: append-only log, replay projection,
    per-event idempotent fingerprint; latest-decision-wins projection over a
    scope key)
  - agentmemory (consent/scope gating: a subject grants or revokes a scope, and
    the effective permission for a scope is the most recent recorded decision)

Design goals:
  - Append-only JSONL: each line is one self-describing consent record. The log
    is never mutated in place; decisions are resolved by replaying in order.
  - Deterministic fingerprint: the same (subject, scope, granted, evidence)
    always yields the same fingerprint, enabling idempotent writes.
  - Latest-wins: granted_for(scope) returns the most recent decision recorded
    for that scope across all subjects, or False if none.
  - No external dependencies (stdlib only). No LLM, no network, no autoloop.

Each record:
    {"entry_id": str, "ts": float, "subject": str, "scope": str,
     "granted": bool, "evidence": Any, "fingerprint": str}
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from typing import Any, Dict, List, Optional


def _fingerprint(
    subject: str,
    scope: str,
    granted: bool,
    evidence: Any,
) -> str:
    """Stable content hash of a consent decision.

    Canonical JSON (sorted keys, no whitespace) binds subject, scope, the
    boolean decision, and the evidence payload together so identical decisions
    always produce identical fingerprints.
    """
    canon = json.dumps(
        {
            "subject": subject,
            "scope": scope,
            "granted": bool(granted),
            "evidence": evidence,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


class ConsentLog:
    """Append-only store of consent decisions with replay and latest-wins lookup.

    Every mutating operation is an append. State (the effective decision per
    scope) is always derived by replaying the log, never stored as truth. This
    matches the append-only, replay-projection discipline of LoopX/agentmemory.
    """

    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        self._seen: Dict[str, str] = {}  # entry_id -> fingerprint (idempotency)
        self._load_state()

    def _read_lines(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        out: List[Dict[str, Any]] = []
        with open(self.path, "r", encoding="utf-8") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw)
                except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
                    continue
                if isinstance(rec, dict):
                    out.append(rec)
        return out

    def _load_state(self) -> None:
        self._seen = {}
        for rec in self._read_lines():
            ident = str(rec.get("entry_id", ""))
            fp = str(rec.get("fingerprint", ""))
            if ident and fp:
                self._seen[ident] = fp

    def record(
        self,
        subject: str,
        scope: str,
        granted: bool,
        evidence: Any = None,
        entry_id: Optional[str] = None,
    ) -> str:
        """Append one consent decision. Idempotent on (entry_id OR fingerprint).

        Returns the entry_id. If an identical decision already exists (same
        entry_id and identical fingerprint) nothing new is written and the prior
        id is returned, so a double-send is a no-op rather than a duplicate.

        Raises ValueError if an entry_id is reused with different content.
        """
        with self._lock:
            fp = _fingerprint(subject, scope, granted, evidence)
            ident = entry_id or fp
            prior = self._seen.get(ident)
            if prior is not None:
                if prior != fp:
                    raise ValueError(
                        "entry id reused with different immutable content"
                    )
                return ident
            ts = time.time()
            rec = {
                "entry_id": ident,
                "ts": ts,
                "subject": subject,
                "scope": scope,
                "granted": bool(granted),
                "evidence": evidence,
                "fingerprint": fp,
            }
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
            self._seen[ident] = fp
            return ident

    def replay(self) -> List[Dict[str, Any]]:
        """Return all consent records in append order (read-only snapshot)."""
        return self._read_lines()

    def granted_for(self, scope: str) -> bool:
        """Return the latest decision recorded for ``scope``.

        Consent decisions are latest-wins per scope: if the most recent record
        for the scope is ``granted=True`` this returns True, otherwise False.
        A scope with no recorded decision returns False (fail-closed).
        """
        decision: bool = False
        found = False
        for rec in self._read_lines():
            if str(rec.get("scope", "")) != scope:
                continue
            found = True
            decision = bool(rec.get("granted", False))
        return found and decision


__all__ = ["ConsentLog"]
