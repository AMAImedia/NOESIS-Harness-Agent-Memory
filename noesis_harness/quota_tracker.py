"""noesis_harness/quota_tracker.py

Append-only quota usage tracker (LoopX).

LoopX spends budget units by appending a validated event and never
decrements on failure. This module borrows that pattern for per-scope
quota accounting: usage is an append-only JSONL log, and the consumed
amount per scope is always a deterministic replay projection of the log.

Hard rules honoured:
  - stdlib only (json, hashlib, threading, time, os) -- no sqlite, no LLM.
  - append-only state: record() only ever appends a line; it never edits
    or rewrites prior entries.
  - idempotency: a write is a no-op if the same (entry_id, fingerprint)
    pair has already been recorded, so a double-send cannot double-count.
  - deterministic core: used()/remaining() are pure functions of the log.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from typing import Any, Dict, Optional, Tuple


class QuotaTracker:
    """Append-only, idempotent per-scope quota usage tracker.

    The backing file is a JSONL log. Each ``record`` call appends one line
    carrying a sha256 fingerprint of its content. ``used`` and ``remaining``
    are computed purely by replaying the log, so the tracker is safe to
    reconstruct from disk at any time.
    """

    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        parent = os.path.dirname(os.path.abspath(self.path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        if not os.path.exists(self.path):
            open(self.path, "a", encoding="utf-8").close()
        self._load()

    def _load(self) -> None:
        self._index: Dict[Tuple[str, str], Dict[str, Any]] = {}
        if not os.path.exists(self.path):
            return
        with open(self.path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                self._index[(entry.get("entry_id", ""), entry.get("fingerprint", ""))] = entry

    @staticmethod
    def _fingerprint(scope: str, amount: int, entry_id: Optional[str]) -> str:
        payload = json.dumps(
            {"scope": scope, "amount": int(amount), "entry_id": entry_id},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def record(self, scope: str, amount: int, entry_id: Optional[str] = None) -> Dict[str, Any]:
        """Append a usage event for ``scope``.

        Idempotent: if the same ``entry_id`` + fingerprint has already been
        recorded, the call is a no-op and the existing entry is returned with
        ``recorded=False``. Returns a dict describing the outcome.
        """
        amount = int(amount)
        fingerprint = self._fingerprint(scope, amount, entry_id)
        key = (entry_id if entry_id is not None else "", fingerprint)
        with self._lock:
            if key in self._index:
                return {**self._index[key], "recorded": False}
            entry = {
                "scope": scope,
                "amount": amount,
                "entry_id": entry_id,
                "fingerprint": fingerprint,
                "ts": time.time(),
            }
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, sort_keys=True) + "\n")
            self._index[key] = entry
            return {**entry, "recorded": True}

    def used(self, scope: str) -> int:
        """Deterministic replay: total recorded amount for ``scope``."""
        with self._lock:
            return sum(e["amount"] for e in self._index.values() if e["scope"] == scope)

    def remaining(self, scope: str, limit: int) -> int:
        """Amount left under ``limit`` for ``scope`` (never negative)."""
        return max(0, int(limit) - self.used(scope))

    def scopes(self):
        with self._lock:
            return sorted({e["scope"] for e in self._index.values()})
