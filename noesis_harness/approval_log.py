"""noesis_harness/approval_log.py

Append-only human-in-the-loop approval events with deterministic replay.

Patterns adapted from:
  - LoopX (AppendOnlyStateEventStore: append-only log, replay projection,
    per-event idempotent fingerprint; latest-decision-wins projection over a
    request id)
  - agentmemory (content-addressable ids + append-only records so a double-send
    is absorbed rather than duplicated)

Design goals:
  - Append-only JSONL: each line is one self-describing event (either a request
    for approval, or an approval/denial decision). The log is never mutated in
    place; state is always resolved by replaying in order.
  - Human-in-the-loop gate: a request starts "pending"; the first matching
    decision (approve or deny) moves it to "approved"/"denied". Unknown ids
    resolve to None (fail-closed so callers must check before acting).
  - Idempotent writes: request() is idempotent on entry_id; approve()/deny() are
    idempotent on (request_id, event type, approver, reason). A double-send is a
    no-op, not a duplicate. Reusing an id with conflicting content raises.
  - No external dependencies (stdlib only). No LLM, no network, no autoloop.

Each record:
    request : {"event": "request", "request_id": str, "action": str,
               "requester": str, "ts": float, "fingerprint": str}
    approve : {"event": "approve", "request_id": str, "approver": str,
               "ts": float, "fingerprint": str}
    deny    : {"event": "deny", "request_id": str, "approver": str,
               "reason": str, "ts": float, "fingerprint": str}
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from typing import Any, Dict, List, Optional

STATE_PENDING = "pending"
STATE_APPROVED = "approved"
STATE_DENIED = "denied"


def _fingerprint(*parts: Any) -> str:
    """Stable content hash binding the given parts together (sha256)."""
    canon = json.dumps(
        list(parts),
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


class ApprovalLog:
    """Append-only store of approval requests and their decisions.

    State for a request is always derived by replaying the log, never stored as
    truth. This matches the append-only, replay-projection discipline of
    LoopX / agentmemory.
    """

    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        self._seen: Dict[str, str] = {}  # entry/request id -> request fingerprint
        self._decision_seen: set = set()  # decision fingerprints already appended
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
        self._decision_seen = set()
        for rec in self._read_lines():
            event = str(rec.get("event", ""))
            if event == "request":
                ident = str(rec.get("request_id", ""))
                fp = str(rec.get("fingerprint", ""))
                if ident and fp:
                    self._seen[ident] = fp
            else:
                fp = str(rec.get("fingerprint", ""))
                if fp:
                    self._decision_seen.add(fp)

    def request(
        self,
        action: str,
        requester: str,
        entry_id: Optional[str] = None,
    ) -> str:
        """Append one approval request. Idempotent on entry_id.

        Returns the request_id. If an identical request (same entry_id and
        identical content fingerprint) already exists, nothing new is written and
        the prior id is returned, so a double-send is a no-op, not a duplicate.

        Raises ValueError if an entry_id is reused with different immutable content.
        """
        with self._lock:
            fp = _fingerprint("request", action, requester)
            ident = entry_id or fp
            prior = self._seen.get(ident)
            if prior is not None:
                if prior != fp:
                    raise ValueError(
                        "request id reused with different immutable content"
                    )
                return ident
            rec = {
                "event": "request",
                "request_id": ident,
                "action": action,
                "requester": requester,
                "ts": time.time(),
                "fingerprint": fp,
            }
            self._append(rec)
            self._seen[ident] = fp
            return ident

    def approve(self, request_id: str, approver: str) -> None:
        """Append an approval decision for request_id. Idempotent on fingerprint.

        No-op (not a duplicate) if the exact same approval was already recorded.
        Raises ValueError if the request_id is unknown, or if a conflicting
        decision (deny) already resolved it.
        """
        self._decide("approve", request_id, approver, reason=None)

    def deny(self, request_id: str, approver: str, reason: str) -> None:
        """Append a denial decision for request_id. Idempotent on fingerprint.

        No-op (not a duplicate) if the exact same denial was already recorded.
        Raises ValueError if the request_id is unknown, or if a conflicting
        decision (approve) already resolved it.
        """
        self._decide("deny", request_id, approver, reason=reason)

    def _decide(
        self,
        event: str,
        request_id: str,
        approver: str,
        reason: Optional[str],
    ) -> None:
        with self._lock:
            if request_id not in self._seen:
                raise ValueError("unknown request id: %s" % request_id)
            fp = _fingerprint(event, request_id, approver, reason)
            if fp in self._decision_seen:
                return
            current = self._resolve(request_id)
            if current is not None and current != STATE_PENDING and current != event:
                raise ValueError(
                    "request already %s; cannot %s" % (current, event)
                )
            rec = {
                "event": event,
                "request_id": request_id,
                "approver": approver,
                "ts": time.time(),
                "fingerprint": fp,
            }
            if event == "deny":
                rec["reason"] = reason
            self._append(rec)
            self._decision_seen.add(fp)

    def _append(self, rec: Dict[str, Any]) -> None:
        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")

    def state(self, request_id: str) -> Optional[str]:
        """Return 'pending' / 'approved' / 'denied' for request_id.

        Returns None for an unknown request id (fail-closed). The first decision
        recorded for a request wins; later decisions are rejected at write time.
        """
        return self._resolve(request_id)

    def _resolve(self, request_id: str) -> Optional[str]:
        if request_id not in self._seen:
            return None
        result: Optional[str] = STATE_PENDING
        for rec in self._read_lines():
            if str(rec.get("request_id", "")) != request_id:
                continue
            event = str(rec.get("event", ""))
            if event == "approve":
                result = STATE_APPROVED
                break
            if event == "deny":
                result = STATE_DENIED
                break
        return result

    def replay(self) -> List[Dict[str, Any]]:
        """Return all approval events in append order (read-only snapshot)."""
        return [dict(r) for r in self._read_lines()]


__all__ = ["ApprovalLog", "STATE_PENDING", "STATE_APPROVED", "STATE_DENIED"]
