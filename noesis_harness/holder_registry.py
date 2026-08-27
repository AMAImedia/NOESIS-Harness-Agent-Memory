"""noesis_harness/holder_registry.py

Stdlib-only append-only holder registry.

Patterns adapted from:
  - agentmemory (holder/scope scoping: a holder is registered against a scope, and
    the set of active holders for a scope is derived by replaying the log)
  - LoopX (AppendOnlyStateEventStore: the only mutating operation is append, state
    is a replay projection, and each entry carries a deterministic content
    fingerprint so a double-send is a no-op rather than a duplicate)

Design goals:
  - Append-only JSONL: each line is one self-describing holder-registration record.
    The log is never mutated in place; active holders are resolved by replay.
  - Deterministic fingerprint: the same (holder, scope) always yields the same
    fingerprint, so registrations are idempotent and de-duplicated.
  - Latest-wins per (holder, scope): the most recent registration for a holder in a
    scope is the one that counts; re-registering the same holder in the same scope
    simply refreshes it, never creates a duplicate.
  - No external dependencies (stdlib only). No LLM, no network, no autoloop.

Each record:
    {"entry_id": str, "ts": float, "holder": str, "scope": str,
     "fingerprint": str}
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from typing import Any, Dict, List, Optional


def fingerprint(holder: str, scope: str) -> str:
    """Stable content hash binding a holder to a scope.

    Canonical JSON (sorted keys, no whitespace) ensures identical (holder, scope)
    pairs always produce identical fingerprints, which is what makes the registry
    idempotent and de-duplicating.
    """
    canon = json.dumps(
        {"holder": str(holder), "scope": str(scope)},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


class HolderRegistry:
    """Append-only registry of holders per scope with replay and idempotency.

    Every mutating operation is an append. The set of active holders for a scope is
    always derived by replaying the log, never stored as truth. This matches the
    append-only, replay-projection discipline of agentmemory/LoopX.
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

    def register(
        self,
        holder: str,
        scope: str,
        entry_id: Optional[str] = None,
    ) -> str:
        """Register ``holder`` under ``scope``. Idempotent on (entry_id OR fingerprint).

        Returns the entry_id. If an equivalent registration already exists (same
        entry_id and identical fingerprint) nothing new is written and the prior id
        is returned, so a double-send is a no-op rather than a duplicate.

        Raises ValueError if an entry_id is reused with a different (holder, scope).
        """
        with self._lock:
            fp = fingerprint(holder, scope)
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
                "holder": str(holder),
                "scope": str(scope),
                "fingerprint": fp,
            }
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            self._seen[ident] = fp
            return ident

    def replay(self) -> List[Dict[str, Any]]:
        """Return all registration records in append order (read-only snapshot)."""
        return self._read_lines()

    def active_holders(self, scope: Optional[str] = None) -> List[str]:
        """Return the distinct active holders, optionally filtered by ``scope``.

        Latest-wins per (holder, scope): the most recent registration for a holder
        in a scope is the one that counts, so a holder appears at most once per
        scope. Order follows the order of each holder's most recent registration.
        """
        latest: Dict[str, str] = {}  # (holder, scope) -> holder (for ordering)
        order: List[str] = []
        for rec in self._read_lines():
            rec_scope = str(rec.get("scope", ""))
            if scope is not None and rec_scope != str(scope):
                continue
            holder = str(rec.get("holder", ""))
            key = (holder, rec_scope)
            if key not in latest:
                order.append(holder)
                latest[key] = holder
        return list(order)


__all__ = ["HolderRegistry", "fingerprint"]
