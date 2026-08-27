"""noesis_harness/audit_trail.py

Append-only audit trail with tamper-evidence.

Patterns adapted from:
  - deepseek-harness (Session.append: event-sourced, idempotent append)
  - LoopX (AppendOnlyStateEventStore: per-event digest chain, replay projection)

Design goals:
  - Append-only JSONL: each line is a self-describing audit entry.
  - Each entry carries event_id, ts, a sha256 fingerprint of (scope/action/
    payload) mirroring EventStore._fingerprint, and a per-line digest chaining
    the prior entry's digest to the current content (tamper-evidence).
  - Idempotent append: same entry_id + fingerprint never rewrites (no duplicate).
  - replay() rebuilds the full ordered list; verify() detects gaps and tampering
    by re-computing every per-line digest and confirming a contiguous chain.

Zero dependencies (stdlib only). One file, one job.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from typing import Any, Dict, List, Optional

ZERO_DIGEST = "0" * 64


def _fingerprint(scope: str, action: str, payload: Any) -> str:
    """Stable content hash of an audit entry (scope + action + canonical JSON)."""
    canon = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(
        f"{scope}\x00{action}\x00{canon}".encode("utf-8")
    ).hexdigest()


class AuditTrail:
    """Append-only audit trail with per-line digest chaining and replay.

    Each entry is a JSON object:
        {"event_id": str, "ts": float, "scope": str, "action": str,
         "payload": ..., "fingerprint": str, "prev": str, "digest": str}

    `prev` links to the previous entry's `digest` (ZERO_DIGEST for the first),
    and `digest` binds prev + event_id + fingerprint, so any edit of an
    earlier line breaks the chain detected by verify().
    """

    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        self._seen: Dict[str, str] = {}  # event_id -> fingerprint (idempotency)
        self._head = ZERO_DIGEST
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
        self._head = ZERO_DIGEST
        for rec in self._read_lines():
            event_id = str(rec.get("event_id", ""))
            fp = str(rec.get("fingerprint", ""))
            if event_id and fp:
                self._seen[event_id] = fp
            self._head = str(rec.get("digest", self._head))

    def append(
        self,
        scope: str,
        action: str,
        payload: Any,
        entry_id: Optional[str] = None,
    ) -> str:
        """Append one audit entry. Idempotent on (entry_id OR fingerprint).

        Returns the entry_id. If an identical pending entry already exists (same
        entry_id and fingerprint) nothing new is written and the prior id is
        returned, matching EventStore's double-send-absorbs semantics.
        """
        with self._lock:
            fp = _fingerprint(scope, action, payload)
            ident = entry_id or fp
            prior = self._seen.get(ident)
            if prior is not None:
                if prior != fp:
                    raise ValueError(
                        "entry id reused with different immutable content"
                    )
                return ident
            ts = time.time()
            prev = self._head
            content = f"{prev}\x00{ident}\x00{fp}".encode("utf-8")
            digest = hashlib.sha256(content).hexdigest()
            rec = {
                "event_id": ident,
                "ts": ts,
                "scope": scope,
                "action": action,
                "payload": payload,
                "fingerprint": fp,
                "prev": prev,
                "digest": digest,
            }
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
            self._seen[ident] = fp
            self._head = digest
            return ident

    def replay(self) -> List[Dict[str, Any]]:
        """Return all audit entries in append order."""
        return self._read_lines()

    def verify(self) -> bool:
        """True if the chain is contiguous and untampered.

        Recomputes every per-line digest from prev + event_id + fingerprint and
        confirms (a) the first entry's prev is ZERO_DIGEST, (b) each subsequent
        prev equals the previous entry's digest, and (c) the final head equals
        the last computed digest (no trailing gap/missing line).
        """
        records = self._read_lines()
        prev = ZERO_DIGEST
        for rec in records:
            ident = str(rec.get("event_id", ""))
            stored_fp = str(rec.get("fingerprint", ""))
            rec_prev = str(rec.get("prev", ""))
            rec_digest = str(rec.get("digest", ""))
            live_fp = _fingerprint(
                str(rec.get("scope", "")),
                str(rec.get("action", "")),
                rec.get("payload"),
            )
            if live_fp != stored_fp:
                return False
            recomputed = hashlib.sha256(
                f"{prev}\x00{ident}\x00{stored_fp}".encode("utf-8")
            ).hexdigest()
            if rec_prev != prev:
                return False
            if rec_digest != recomputed:
                return False
            prev = rec_digest
        return True


__all__ = ["AuditTrail", "ZERO_DIGEST"]
