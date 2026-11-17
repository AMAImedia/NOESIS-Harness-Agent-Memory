"""noesis_harness/extraction_queue.py

Single-writer mutex plus a trailing extraction queue for background memory
extraction.

Borrowed pattern (concept + rationale):
  - claude-code-book, Part-2 chapter 06: "automatic memory extraction via
    fork". A background fork performs memory extraction after a session's turn
    completes. Three rules keep it correct and cheap:
      1. A single-writer mutex per session. If the main agent already claimed
         the extraction slot, the background worker skips its own extraction
         instead of racing or double-writing.
      2. A throttle counter. Background extractions only run once the session
         has accumulated enough completed turns since the last extraction, so a
         busy session does not fork on every turn.
      3. A trailing extraction queue. When a claim fails because another
         extraction is in flight, the worker records the newest payload in a
         single trailing slot (later payloads replace earlier pending ones).
         Once the in-flight extraction finishes it drains the trailing slot and
         runs at most one extra pass. A completed session's extraction is
         therefore never dropped, no matter how the timing falls.

This module contains only the pure coordination state machine: no forking, no
threads spawned, no I/O, no clocks. The caller decides what "extract" means and
when turns complete, which keeps the coordinator deterministic and replays
identically for a given call sequence. A threading.Lock only guards individual
method bodies so the state machine is safe to share inside one process.

Stdlib only. Python 3.9 compatible.
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional

__all__ = ["ExtractionCoordinator", "ExtractionWorker"]

_MISSING = object()


class ExtractionCoordinator:
    """Tracks per-session claim, throttle counter and trailing payload slot.

    Args:
        throttle: minimum number of completed turns that must elapse between
            two background extractions for the same session. Must be >= 1.
    """

    def __init__(self, throttle: int = 1) -> None:
        if throttle < 1:
            raise ValueError("throttle must be >= 1")
        self._throttle = throttle
        self._lock = threading.Lock()
        self._sessions = {}

    def _state(self, session_id: str) -> dict:
        state = self._sessions.get(session_id)
        if state is None:
            state = {
                "turns": 0,
                "extractions": 0,
                "claimed": False,
                "last_turn": None,
                "trailing": _MISSING,
            }
            self._sessions[session_id] = state
        return state

    def note_turn(self, session_id: str) -> int:
        """Increment and return the completed-turn counter for a session."""
        with self._lock:
            state = self._state(session_id)
            state["turns"] += 1
            return state["turns"]

    def try_claim(self, session_id: str) -> bool:
        """Attempt the single-writer claim for a session.

        Returns True only when no extraction is currently claimed for the
        session and the throttle has elapsed since the last completed
        extraction. A successful claim stays held until release() is called;
        claiming itself does not release anything.
        """
        with self._lock:
            state = self._state(session_id)
            if state["claimed"]:
                return False
            last = state["last_turn"]
            if last is not None and (state["turns"] - last) < self._throttle:
                return False
            state["claimed"] = True
            return True

    def release(self, session_id: str) -> bool:
        """Release the claim for a session. False when it was not claimed."""
        with self._lock:
            state = self._state(session_id)
            if not state["claimed"]:
                return False
            state["claimed"] = False
            return True

    def is_claimed(self, session_id: str) -> bool:
        """Return True while the session's extraction claim is held."""
        with self._lock:
            return bool(self._state(session_id)["claimed"])

    def enqueue_trailing(self, session_id: str, payload: Any) -> None:
        """Record at most one trailing extraction payload for a session.

        Later calls replace the earlier pending payload: the slot always holds
        the newest payload, so one drain pass is enough to avoid dropping a
        completed session's extraction.
        """
        with self._lock:
            state = self._state(session_id)
            state["trailing"] = payload
        return None

    def _take_trailing(self, session_id: str):
        """Internal: pop the trailing slot, returning (found, payload)."""
        with self._lock:
            state = self._state(session_id)
            if state["trailing"] is _MISSING:
                return (False, None)
            payload = state["trailing"]
            state["trailing"] = _MISSING
            return (True, payload)

    def drain_trailing(self, session_id: str) -> Optional[Any]:
        """Pop and return the pending trailing payload, or None when none."""
        found, payload = self._take_trailing(session_id)
        return payload if found else None

    def _has_trailing(self, session_id: str) -> bool:
        """Internal: True when a trailing payload is currently pending."""
        with self._lock:
            return self._state(session_id)["trailing"] is not _MISSING

    def pending(self) -> List[str]:
        """Return sorted session ids that currently hold a trailing payload."""
        with self._lock:
            ids = [
                sid
                for sid, state in self._sessions.items()
                if state["trailing"] is not _MISSING
            ]
        return sorted(ids)

    def stats(self, session_id: str) -> Dict:
        """Return a snapshot dict for a session.

        Keys: turns, extractions, claimed, trailing.
        """
        with self._lock:
            state = self._state(session_id)
            return {
                "turns": state["turns"],
                "extractions": state["extractions"],
                "claimed": bool(state["claimed"]),
                "trailing": state["trailing"] is not _MISSING,
            }

    def record_extraction(self, session_id: str) -> None:
        """Mark an extraction as completed and refresh the throttle anchor."""
        with self._lock:
            state = self._state(session_id)
            state["extractions"] += 1
            state["last_turn"] = state["turns"]
        return None


class ExtractionWorker:
    """Runs one background extraction pass for a session.

    Args:
        coordinator: the shared ExtractionCoordinator.
        extract: callable invoked as extract(session_id, payload) -> Any.
    """

    def __init__(
        self,
        coordinator: ExtractionCoordinator,
        extract: Callable[[str, Any], Any],
    ) -> None:
        self._coordinator = coordinator
        self._extract = extract

    def run(self, session_id: str, payload: Any) -> Dict:
        """Attempt extraction, falling back to the trailing slot.

        When the claim succeeds the payload is extracted, recorded and the
        claim released; then any trailing payload recorded meanwhile is drained
        and processed in at most one extra pass. When the claim fails the
        payload is stored as the session's single trailing extraction and no
        extraction runs. A failed claim never raises; an exception raised by
        extract propagates only after the claim has been released.
        """
        coordinator = self._coordinator
        if not coordinator.try_claim(session_id):
            coordinator.enqueue_trailing(session_id, payload)
            return {"processed": 0, "trailing_remaining": True}

        try:
            self._extract(session_id, payload)
            coordinator.record_extraction(session_id)
        except BaseException:
            coordinator.release(session_id)
            raise

        coordinator.release(session_id)
        processed = 1

        found, trailing_payload = coordinator._take_trailing(session_id)
        if found:
            self._extract(session_id, trailing_payload)
            coordinator.record_extraction(session_id)
            processed += 1

        return {
            "processed": processed,
            "trailing_remaining": coordinator._has_trailing(session_id),
        }
