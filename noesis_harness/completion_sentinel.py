"""File-sentinel completion protocol and idempotent step/lease coordination.

Provenance: patterns ported from the AI-Builder-Club/skills repository.

* ``skills/open-agent-teams/SKILL.md`` and ``scripts/tdel`` describe a
  file-sentinel + result-file completion protocol: a bare in-memory signal is
  silently lost when nobody is waiting and cannot be timed out, so completion is
  published as a ``done`` sentinel file while the payload lives in a separate
  ``result`` file. The waiter polls with a timeout and raises a diagnostic when
  the deadline passes, and per-turn sentinel names prevent cross-talk.
* ``skills/crabbox-setup/assets/setup.sh`` and ``cbx.sh`` describe idempotent
  check-before-act runs: each step inspects state before acting (safe re-run),
  publishes success as a ``ready`` marker file, and leases an external resource
  through a persisted id file with a mandatory explicit release (no auto-stop).

The module is standard-library only and fully deterministic when a clock is
injected, so tests never block on the wall clock.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
from typing import Callable, Dict, List, Optional

DONE_SUFFIX = ".done"
RESULT_SUFFIX = ".result"
READY_SUFFIX = ".ready"
LEASE_SUFFIX = ".lease"

_SAFE = re.compile(r"[^A-Za-z0-9_.-]+")


def _slug(value: str) -> str:
    """Map an arbitrary session/step/resource name onto a safe filename."""
    text = _SAFE.sub("_", str(value)).strip("._") or "item"
    return text


def _atomic_write(path: str, text: str) -> None:
    """Write ``text`` to ``path`` atomically via temp file plus os.replace."""
    directory = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".tmp-", suffix=".part")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def _read_text(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return None


class SentinelTimeout(RuntimeError):
    """Raised when a completion sentinel is not observed within the deadline."""

    def __init__(
        self,
        session: str,
        turn: int,
        elapsed: float,
        last_lines: Optional[List[str]] = None,
    ) -> None:
        self.session = session
        self.turn = turn
        self.last_lines: List[str] = list(last_lines) if last_lines else []
        message = (
            "completion sentinel timeout after %.3fs for session=%s turn=%d"
            % (float(elapsed), session, turn)
        )
        super().__init__(message)


class TurnSentinel:
    """Completion sentinel plus result payload scoped to one session turn."""

    def __init__(self, root: str) -> None:
        self.root = os.path.abspath(root)
        os.makedirs(self.root, exist_ok=True)

    def _base(self, session: str, turn: int) -> str:
        return "%s.t%d" % (_slug(session), int(turn))

    def paths(self, session: str, turn: int) -> Dict[str, str]:
        base = self._base(session, turn)
        return {
            "done": os.path.join(self.root, base + DONE_SUFFIX),
            "result": os.path.join(self.root, base + RESULT_SUFFIX),
        }

    def mark_done(self, session: str, turn: int, result: str) -> str:
        """Atomically publish the result then the done sentinel.

        Idempotent: a repeated call with the same result is a no-op. A call
        whose result differs from an already published one raises ValueError.
        """
        target = self.paths(session, turn)
        existing = _read_text(target["result"])
        if existing is not None and existing != result:
            raise ValueError(
                "completion result conflict for session=%s turn=%d" % (session, int(turn))
            )
        if existing is None:
            _atomic_write(target["result"], result)
        if not os.path.exists(target["done"]):
            _atomic_write(target["done"], "done\n")
        return target["result"]

    def is_done(self, session: str, turn: int) -> bool:
        return os.path.exists(self.paths(session, turn)["done"])

    def read_result(self, session: str, turn: int) -> Optional[str]:
        return _read_text(self.paths(session, turn)["result"])

    def wait_for_done(
        self,
        session: str,
        turn: int,
        timeout: float,
        now: Callable[[], float],
        sleep: Callable[[float], None],
        poll: float = 0.05,
        last_lines: Optional[Callable[[str], List[str]]] = None,
    ) -> str:
        """Poll for the done sentinel, returning the result payload.

        ``now`` and ``sleep`` are injected so callers control the clock. On
        deadline expiry a SentinelTimeout is raised, carrying the elapsed time
        and optional diagnostic lines gathered from the result path.
        """
        result_path = self.paths(session, turn)["result"]
        start = now()
        while True:
            if self.is_done(session, turn):
                return self.read_result(session, turn) or ""
            elapsed = now() - start
            if elapsed >= timeout:
                lines = list(last_lines(result_path)) if last_lines is not None else []
                raise SentinelTimeout(session, turn, elapsed, lines)
            sleep(poll)

    def pending_turns(self, session: str) -> List[int]:
        """Turns holding a result without done, or done without a result."""
        prefix = _slug(session) + ".t"
        result_turns = set()
        done_turns = set()
        try:
            names = os.listdir(self.root)
        except OSError:
            return []
        for name in names:
            if not name.startswith(prefix):
                continue
            if name.endswith(RESULT_SUFFIX):
                token = name[len(prefix):-len(RESULT_SUFFIX)]
                if token.isdigit():
                    result_turns.add(int(token))
            elif name.endswith(DONE_SUFFIX):
                token = name[len(prefix):-len(DONE_SUFFIX)]
                if token.isdigit():
                    done_turns.add(int(token))
        return sorted(result_turns ^ done_turns)


class StepMarker:
    """Check-before-act step runner publishing a READY marker on success."""

    def __init__(self, root: str) -> None:
        self.root = os.path.abspath(root)
        os.makedirs(self.root, exist_ok=True)

    def _path(self, name: str) -> str:
        return os.path.join(self.root, _slug(name) + READY_SUFFIX)

    def is_ready(self, name: str) -> bool:
        return os.path.exists(self._path(name))

    def mark_ready(self, name: str, detail: str = "") -> str:
        """Publish the READY marker. First write wins; re-runs are a no-op."""
        path = self._path(name)
        if not os.path.exists(path):
            _atomic_write(path, detail)
        return path

    def run_once(self, name: str, action: Callable[[], str]) -> Dict:
        """Run ``action`` only if the step is not already ready.

        If an exception propagates from ``action`` the READY marker is not
        written, so a later re-run is allowed to try again.
        """
        path = self._path(name)
        if os.path.exists(path):
            return {"ran": False, "detail": _read_text(path) or ""}
        detail = action()
        _atomic_write(path, detail)
        return {"ran": True, "detail": detail}


class ResourceLease:
    """Persisted, deterministic lease over an external resource.

    Callers MUST release explicitly via :meth:`release`; there is no auto-stop
    and no background reaper. ``acquire`` is safe to call repeatedly by the same
    holder (idempotent) and refuses to steal a live lease from another holder.
    """

    def __init__(self, root: str) -> None:
        self.root = os.path.abspath(root)
        os.makedirs(self.root, exist_ok=True)

    def _path(self, name: str) -> str:
        return os.path.join(self.root, _slug(name) + LEASE_SUFFIX)

    @staticmethod
    def lease_id(name: str, holder: str) -> str:
        return hashlib.sha256((name + holder).encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _expired(record: Dict, current: float) -> bool:
        expires = record.get("expires_at")
        if expires is None:
            return False
        return current >= float(expires)

    def _read(self, path: str) -> Optional[Dict]:
        text = _read_text(path)
        if text is None:
            return None
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    def acquire(
        self,
        name: str,
        holder: str,
        now: Optional[Callable[[], float]] = None,
        ttl_seconds: Optional[float] = None,
    ) -> str:
        """Lease ``name`` for ``holder`` and return the deterministic lease id.

        A live lease held by another holder raises RuntimeError. An expired
        lease is replaceable. ``ttl_seconds=None`` means the lease never
        expires; otherwise expiry is measured against the injected ``now``.
        """
        path = self._path(name)
        current = now() if now is not None else time.time()
        existing = self._read(path)
        if existing is not None and not self._expired(existing, current):
            if existing.get("holder") == holder:
                return str(existing.get("lease_id", self.lease_id(name, holder)))
            raise RuntimeError(
                "resource lease for %s is held by %s" % (name, existing.get("holder"))
            )
        lease = self.lease_id(name, holder)
        record = {
            "name": name,
            "holder": holder,
            "lease_id": lease,
            "acquired_at": current,
            "ttl_seconds": ttl_seconds,
            "expires_at": None if ttl_seconds is None else current + float(ttl_seconds),
        }
        _atomic_write(path, json.dumps(record, sort_keys=True))
        return lease

    def holder(
        self, name: str, now: Optional[Callable[[], float]] = None
    ) -> Optional[str]:
        record = self._read(self._path(name))
        if record is None:
            return None
        current = now() if now is not None else time.time()
        if self._expired(record, current):
            return None
        return record.get("holder")

    def release(self, name: str, holder: str) -> bool:
        """Release only when ``holder`` owns the lease; returns False otherwise."""
        path = self._path(name)
        record = self._read(path)
        if record is None or record.get("holder") != holder:
            return False
        os.remove(path)
        return True


__all__ = [
    "DONE_SUFFIX",
    "RESULT_SUFFIX",
    "READY_SUFFIX",
    "LEASE_SUFFIX",
    "SentinelTimeout",
    "TurnSentinel",
    "StepMarker",
    "ResourceLease",
]
