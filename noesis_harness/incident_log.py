"""noesis_harness/incident_log.py

Append-only incident records with open/close lifecycle and replay projection.

Patterns adapted from:
  - LoopX (AppendOnlyStateEventStore: per-event digest chain, replay projection,
    typed statuses as string enums, idempotent append)
  - agentmemory (append-only incident event log, status as derived projection)

Design goals:
  - Append-only JSONL: each line is a self-describing incident event ("open" or
    "close"). The event log is never mutated; status is a replay projection.
  - Each event carries event_id, ts, a sha256 fingerprint of (type/incident_id/
    payload), a per-line digest chaining the prior event's digest (tamper-evidence),
    and a typed status enum ("open" / "closed").
  - Idempotent append: a double-send of the same event (same event_id and
    fingerprint) is absorbed as a no-op, never a duplicate.
  - status(incident_id) is a pure projection over the replayed event log and does
    not mutate stored state.

Zero dependencies (stdlib only). One file, one job.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from typing import Any, Dict, List, Optional

STATUS_OPEN = "open"
STATUS_CLOSED = "closed"
ZERO_DIGEST = "0" * 64


def _fingerprint(kind: str, incident_id: str, payload: Dict[str, Any]) -> str:
    """Stable content hash of an incident event (kind + incident_id + canonical JSON)."""
    canon = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(
        f"{kind}\x00{incident_id}\x00{canon}".encode("utf-8")
    ).hexdigest()


class IncidentLog:
    """Append-only incident log with open/close lifecycle and replay.

    Each event is a JSON object:
        {"event_id": str, "ts": float, "type": "open"|"close",
         "incident_id": str, "severity": str, "detail": str,
         "resolution": str, "fingerprint": str, "prev": str, "digest": str}

    `prev` links to the previous event's `digest` (ZERO_DIGEST for the first),
    and `digest` binds prev + event_id + fingerprint, so any edit of an earlier
    line breaks the chain. status() is a pure projection: it never mutates state.
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

    def _append_event(
        self,
        kind: str,
        incident_id: str,
        severity: str,
        detail: str,
        resolution: str,
    ) -> str:
        payload: Dict[str, Any] = {
            "severity": severity,
            "detail": detail,
            "resolution": resolution,
        }
        fp = _fingerprint(kind, incident_id, payload)
        ident = fp
        prior = self._seen.get(ident)
        if prior is not None:
            return ident
        ts = time.time()
        prev = self._head
        content = f"{prev}\x00{ident}\x00{fp}".encode("utf-8")
        digest = hashlib.sha256(content).hexdigest()
        rec = {
            "event_id": ident,
            "ts": ts,
            "type": kind,
            "incident_id": incident_id,
            "severity": severity,
            "detail": detail,
            "resolution": resolution,
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

    def open(self, incident_id: str, severity: str, detail: str) -> str:
        """Append an 'open' event. Idempotent on (incident_id, severity, detail).

        Returns the event_id (content hash). A re-open with identical content is
        absorbed; a re-open of the same incident_id with different content raises
        ValueError because the event log is immutable.
        """
        with self._lock:
            payload = {"severity": severity, "detail": detail, "resolution": ""}
            fp = _fingerprint("open", incident_id, payload)
            existing = self._seen.get(fp)
            if existing is not None:
                return fp
            for rec in self._read_lines():
                if str(rec.get("incident_id", "")) == incident_id and str(rec.get("type", "")) == "open":
                    raise ValueError(
                        "incident %r already opened with different immutable content"
                        % incident_id
                    )
            return self._append_event("open", incident_id, severity, detail, "")

    def close(self, incident_id: str, resolution: str) -> str:
        """Append a 'close' event. Idempotent on (incident_id, resolution).

        Returns the event_id. Closing an incident that was never opened raises
        KeyError (you cannot close an unknown incident).
        """
        with self._lock:
            opened = False
            for rec in self._read_lines():
                if str(rec.get("incident_id", "")) == incident_id:
                    opened = True
                    break
            if not opened:
                raise KeyError(incident_id)
            payload = {"severity": "", "detail": "", "resolution": resolution}
            fp = _fingerprint("close", incident_id, payload)
            if self._seen.get(fp) is not None:
                return fp
            return self._append_event("close", incident_id, "", "", resolution)

    def status(self, incident_id: str) -> str:
        """Return the current status of an incident: 'open' or 'closed'.

        The status is a pure replay projection over the event log. An unknown
        incident_id raises KeyError. This method never mutates stored state.
        """
        current: Optional[str] = None
        for rec in self._read_lines():
            if str(rec.get("incident_id", "")) != incident_id:
                continue
            kind = str(rec.get("type", ""))
            if kind == "open":
                current = STATUS_OPEN
            elif kind == "close":
                current = STATUS_CLOSED
        if current is None:
            raise KeyError(incident_id)
        return current

    def replay(self) -> List[Dict[str, Any]]:
        """Return all incident events in append order (fresh copies)."""
        return [dict(rec) for rec in self._read_lines()]


__all__ = [
    "IncidentLog",
    "STATUS_OPEN",
    "STATUS_CLOSED",
    "ZERO_DIGEST",
]
