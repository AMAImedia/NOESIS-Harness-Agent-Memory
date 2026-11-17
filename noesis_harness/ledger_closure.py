"""noesis_harness/ledger_closure.py

Append-only causal ledger with a mandatory closure invariant.

Provenance:
  Ported from the harness-books repository, book 1:
    - chapter-03 (query-loop heartbeat: "the ledger is closed") -- every
      committed intent must be paired with a terminal event before the loop
      may be considered closed.
    - chapter-04 (interrupt semantics) -- an interrupted intent is not
      allowed to simply disappear; it must be explicitly terminalised.
    - chapter-06 (abort as a semantic failure state) -- abort is a first
      class outcome, not an absence of outcome. A dangling intent is a bug,
      so closure is mandatory rather than best-effort.

Design goals:
  - Append-only JSONL log at ``path``. Each line has the same shape as the
    project's ``EventStore``: ``{"event_id", "type", "payload", "seq"}``.
  - Idempotent at the persistence layer: the same ``event_id`` with the same
    content is never written twice, so replay is deterministic.
  - Mandatory closure: an intent opened with ``intent_opened`` must be closed
    with ``intent_closed``. Interrupted or aborted work is closed with a
    synthetic terminal record instead of being left dangling.
  - Crash-safe: a malformed tail is repaired on construction; only the last
    partial line may be discarded. Earlier corruption is a hard error.
  - Deterministic: state is a pure replay of the log and the digest is taken
    over canonical JSON, so two readers of the same file agree exactly.

Zero third-party dependencies (standard library only). One file, one job.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from typing import Any, Dict, List, Optional, Set

OPEN_TYPE = "intent_opened"
CLOSE_TYPE = "intent_closed"
_OPEN_PREFIX = "open:"
_CLOSE_PREFIX = "close:"


class LedgerError(RuntimeError):
    """A ledger invariant was violated (conflict, corrupt log, bad close)."""


def _canonical_json(obj: Any) -> str:
    """Canonical JSON: sorted keys, compact separators, UTF-8 preserved."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _fingerprint(event_type: str, payload: Any) -> str:
    """Stable content hash of an event (type + canonical JSON payload)."""
    canon = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(
        ("%s\x00%s" % (event_type, canon)).encode("utf-8")
    ).hexdigest()


class LedgerClosure:
    """Append-only causal ledger where closure of every intent is mandatory.

    The ledger tracks a set of intents. Each intent is opened once and closed
    exactly once. ``pending`` intents are those that were opened but never
    reached a terminal record; they are the ones a query loop must resolve
    (normally via :meth:`close_all_pending`) before the ledger is considered
    closed.
    """

    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        self._seen: Set[str] = set()
        self._fingerprints: Dict[str, str] = {}
        self._seq = 0
        self._opened: Set[str] = set()
        self._closed: Set[str] = set()
        self._kinds: Dict[str, str] = {}
        self._outcomes: Dict[str, str] = {}
        self._synthetic: Dict[str, bool] = {}
        self._load()

    # ------------------------------------------------------------------
    # loading / replay
    # ------------------------------------------------------------------
    def _read_records(self) -> List[Dict[str, Any]]:
        """Read every well-formed record, repairing only a malformed tail."""
        if not os.path.exists(self.path):
            return []
        with open(self.path, "rb") as source:
            raw_lines = source.read().splitlines(keepends=True)
        records: List[Dict[str, Any]] = []
        valid_offset = 0
        for index, raw_line in enumerate(raw_lines):
            if not raw_line.strip():
                valid_offset += len(raw_line)
                continue
            try:
                record = json.loads(raw_line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
                if index == len(raw_lines) - 1:
                    with open(self.path, "r+b") as fh:
                        fh.truncate(valid_offset)
                    break
                raise LedgerError("ledger corruption before tail") from exc
            if not isinstance(record, dict):
                if index == len(raw_lines) - 1:
                    with open(self.path, "r+b") as fh:
                        fh.truncate(valid_offset)
                    break
                raise LedgerError("ledger record must be an object")
            valid_offset += len(raw_line)
            records.append(record)
        return records

    def _load(self) -> None:
        for record in self._read_records():
            event_id = str(record.get("event_id", ""))
            event_type = str(record.get("type", ""))
            payload = record.get("payload")
            fingerprint = _fingerprint(event_type, payload)
            prior = self._fingerprints.get(event_id)
            if prior is not None and prior != fingerprint:
                raise LedgerError("ledger event id reused with different content")
            self._seen.add(event_id)
            self._fingerprints[event_id] = fingerprint
            seq = record.get("seq")
            if isinstance(seq, int) and seq > self._seq:
                self._seq = seq
            self._apply(event_type, payload)

    def _apply(self, event_type: str, payload: Any) -> None:
        """Fold one replayed event into the intent projection."""
        if not isinstance(payload, dict):
            return
        intent_id = payload.get("intent_id")
        if not intent_id:
            return
        intent_id = str(intent_id)
        if event_type == OPEN_TYPE:
            if intent_id in self._opened or intent_id in self._closed:
                return
            self._opened.add(intent_id)
            self._kinds[intent_id] = str(payload.get("kind", ""))
        elif event_type == CLOSE_TYPE:
            if intent_id not in self._opened:
                raise LedgerError(
                    "ledger close without open: %s" % intent_id
                )
            outcome = payload.get("outcome")
            if intent_id in self._closed:
                if self._outcomes.get(intent_id) != outcome:
                    raise LedgerError(
                        "conflicting close for intent: %s" % intent_id
                    )
                return
            self._closed.add(intent_id)
            self._outcomes[intent_id] = str(outcome)
            self._synthetic[intent_id] = bool(payload.get("synthetic", False))

    # ------------------------------------------------------------------
    # append
    # ------------------------------------------------------------------
    def _append(self, event_type: str, payload: Dict[str, Any], event_id: str) -> str:
        """Append one record. Idempotent on identical (event_id, content)."""
        fingerprint = _fingerprint(event_type, payload)
        prior = self._fingerprints.get(event_id)
        if prior is not None:
            if prior != fingerprint:
                raise LedgerError("ledger event id reused with different content")
            return event_id
        self._seq += 1
        record = {
            "event_id": event_id,
            "type": event_type,
            "payload": payload,
            "seq": self._seq,
        }
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        self._seen.add(event_id)
        self._fingerprints[event_id] = fingerprint
        return event_id

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def open_intent(
        self, intent_id: str, kind: str, payload: Optional[Dict] = None
    ) -> str:
        """Open an intent and append an ``intent_opened`` event.

        The append layer is idempotent on the derived ``event_id``; the
        logical API is not: opening an intent that is already open or already
        closed raises :class:`LedgerError`.
        """
        if not intent_id:
            raise LedgerError("intent_id is required")
        with self._lock:
            if intent_id in self._opened or intent_id in self._closed:
                raise LedgerError("intent already opened: %s" % intent_id)
            event_id = _OPEN_PREFIX + intent_id
            body = {"intent_id": intent_id, "kind": kind, "payload": payload}
            self._append(OPEN_TYPE, body, event_id)
            self._opened.add(intent_id)
            self._kinds[intent_id] = str(kind)
            return event_id

    def close_intent(
        self,
        intent_id: str,
        outcome: str,
        synthetic: bool = False,
        payload: Optional[Dict] = None,
    ) -> str:
        """Close an intent and append an ``intent_closed`` event.

        Requires a prior open. Closing twice with the same outcome is a no-op
        that returns the existing ``event_id``; a different outcome raises
        :class:`LedgerError`. ``synthetic`` marks a terminal record written on
        behalf of an interrupted or aborted intent.
        """
        if not intent_id:
            raise LedgerError("intent_id is required")
        event_id = _CLOSE_PREFIX + intent_id
        with self._lock:
            if intent_id not in self._opened:
                raise LedgerError("cannot close unopened intent: %s" % intent_id)
            if intent_id in self._closed:
                if self._outcomes.get(intent_id) == outcome:
                    return event_id
                raise LedgerError(
                    "intent already closed with different outcome: %s" % intent_id
                )
            body = {
                "intent_id": intent_id,
                "outcome": outcome,
                "synthetic": bool(synthetic),
                "payload": payload,
            }
            self._append(CLOSE_TYPE, body, event_id)
            self._closed.add(intent_id)
            self._outcomes[intent_id] = str(outcome)
            self._synthetic[intent_id] = bool(synthetic)
            return event_id

    def pending(self) -> List[str]:
        """Sorted intent ids that were opened but never closed."""
        return sorted(self._opened - self._closed)

    def is_closed(self, intent_id: str) -> bool:
        return intent_id in self._closed

    def close_all_pending(
        self, outcome: str, synthetic: bool = True
    ) -> List[str]:
        """Close every pending intent, returning the sorted ids closed."""
        targets = self.pending()
        for intent_id in targets:
            self.close_intent(intent_id, outcome, synthetic=synthetic)
        return sorted(targets)

    def state(self) -> Dict[str, Dict]:
        """Replay projection: intent_id -> kind/outcome/synthetic/closed."""
        projection: Dict[str, Dict] = {}
        for intent_id in sorted(self._opened | self._closed):
            projection[intent_id] = {
                "kind": self._kinds.get(intent_id, ""),
                "outcome": self._outcomes.get(intent_id),
                "synthetic": self._synthetic.get(intent_id, False),
                "closed": intent_id in self._closed,
            }
        return projection

    def count(self) -> int:
        """Number of records appended to the ledger."""
        return len(self._seen)

    def digest(self) -> str:
        """Digest of the replay projection: ``sha256:<canonical state>``."""
        payload = _canonical_json(self.state()).encode("utf-8")
        return "sha256:" + hashlib.sha256(payload).hexdigest()


def closure_summary(ledger: LedgerClosure) -> Dict:
    """Summarise closure health: counts plus the projection digest."""
    projection = ledger.state()
    opened = len(projection)
    closed = sum(1 for entry in projection.values() if entry["closed"])
    synthetic_closed = sum(
        1
        for entry in projection.values()
        if entry["closed"] and entry["synthetic"]
    )
    return {
        "opened": opened,
        "closed": closed,
        "pending": opened - closed,
        "synthetic_closed": synthetic_closed,
        "digest": ledger.digest(),
    }


__all__ = ["LedgerClosure", "LedgerError", "closure_summary"]
