"""Durable leader lease, per-key serialization queue, and resilient sweeper.

Borrowed patterns from:
  - qm (TypeScript), ``src/persistence/leadership.ts``: a durable leadership
    record on disk. A process becomes leader only when the stored record is
    absent, expired, or already names the caller (renewal). An incrementing
    fencing token is persisted on every successful acquisition so downstream
    consumers can reject work from a stale leader that lost the lease.
  - qm, ``src/cron/scheduler.ts``: the scheduler takes the leader lease once per
    tick, so two scheduler processes sharing the same durable lease never fire
    the same tick twice.
  - qm, ``src/util/sweeper.ts`` ``createSweeper``: a run-once sweeper that fires
    on the first tick and then only once the configured interval has elapsed. A
    sweep that throws is captured and does not advance the last-run mark.
  - qm, ``src/util/async.ts`` ``createKeyedQueue``: per-key serialization so
    work for the same key runs one at a time while different keys proceed
    independently.

The port is a clean-room reimplementation, not vendored code. It is
stdlib-only. ``LeaderLease`` is durable (atomic temp+rename writes through
``noesis_harness.atomic_write``) and takes an injected ``now`` so behavior is
deterministic and testable without a real clock. No wall-clock call is made.
"""

from __future__ import annotations

import json
import math
import threading
from typing import Any, Callable, Dict, Optional

from noesis_harness.atomic_write import atomic_write_text, read_text

__all__ = ["LeaseError", "LeaderLease", "KeyedQueue", "Sweeper"]

_RECORD_VERSION = 1


class LeaseError(RuntimeError):
    """Raised when a lease file is corrupt or a lease argument is invalid."""


def _require_holder(holder: str) -> str:
    """Return ``holder`` if it is a non-empty string, else raise LeaseError."""
    if not isinstance(holder, str) or not holder:
        raise LeaseError("holder must be a non-empty string")
    return holder


def _require_ttl(ttl: float) -> float:
    """Return ``ttl`` as a positive finite float, else raise LeaseError."""
    try:
        value = float(ttl)
    except (TypeError, ValueError):
        raise LeaseError("ttl must be a number")
    if math.isnan(value) or math.isinf(value) or value <= 0.0:
        raise LeaseError("ttl must be a positive finite number")
    return value


class LeaderLease:
    """A single-holder durable lease backed by a JSON file.

    The file holds ``{"holder": str|None, "expires_at": float, "fence": int,
    "version": int}``. A lease is *held* when a holder is recorded and the
    supplied ``now`` is strictly before ``expires_at``. Writes are atomic, so a
    reader always sees a complete previous or complete new record.

    Args:
        path: filesystem path of the durable lease file. Parent directories are
            created on the first write.
    """

    def __init__(self, path: str) -> None:
        if not isinstance(path, str) or not path:
            raise LeaseError("path must be a non-empty string")
        self._path = path
        self._lock = threading.RLock()

    @property
    def path(self) -> str:
        """The durable lease file path."""
        return self._path

    def _read(self) -> Optional[Dict[str, Any]]:
        """Return the parsed lease record, or None when the file is missing."""
        raw = read_text(self._path)
        if raw is None or not raw.strip():
            return None
        try:
            data = json.loads(raw)
        except ValueError as exc:
            raise LeaseError(
                "corrupt lease file %r: %s" % (self._path, exc)
            )
        if not isinstance(data, dict):
            raise LeaseError(
                "corrupt lease file %r: expected a JSON object" % self._path
            )
        return data

    def _write(self, holder: Optional[str], expires_at: float, fence: int) -> None:
        """Atomically persist a lease record."""
        record = {
            "version": _RECORD_VERSION,
            "holder": holder,
            "expires_at": float(expires_at),
            "fence": int(fence),
        }
        atomic_write_text(
            self._path, json.dumps(record, sort_keys=True)
        )

    @staticmethod
    def _fence_of(record: Optional[Dict[str, Any]]) -> int:
        """Return the fence from a record, defaulting to 0 when absent."""
        if record is None:
            return 0
        try:
            return int(record.get("fence", 0))
        except (TypeError, ValueError):
            raise LeaseError("corrupt lease file: fence is not an integer")

    @staticmethod
    def _expires_at_of(record: Optional[Dict[str, Any]]) -> float:
        """Return the expiry from a record, defaulting to 0.0 when absent."""
        if record is None:
            return 0.0
        try:
            return float(record.get("expires_at", 0.0))
        except (TypeError, ValueError):
            raise LeaseError("corrupt lease file: expires_at is not a number")

    def try_acquire(self, holder: str, ttl: float, now: float) -> bool:
        """Acquire or renew the lease for ``holder``.

        Succeeds when the lease is free, has expired (``now >= expires_at``),
        or is already held by ``holder``. On success the record is rewritten
        atomically with ``expires_at = now + ttl`` and a fence incremented by
        one. Returns True when ``holder`` holds the lease after the call; a
        non-expired lease held by another holder returns False without a write.
        """
        holder = _require_holder(holder)
        ttl_value = _require_ttl(ttl)
        now_value = float(now)
        with self._lock:
            current = self._read()
            if current is not None:
                current_holder = current.get("holder")
                expires_at = self._expires_at_of(current)
                held = current_holder is not None and now_value < expires_at
                if held and current_holder != holder:
                    return False
            fence = self._fence_of(current) + 1
            self._write(holder, now_value + ttl_value, fence)
            return True

    def renew(self, holder: str, ttl: float, now: float) -> bool:
        """Extend the lease for the current, non-expired holder.

        Returns False when the lease is free, expired, or held by a different
        holder. A successful renew keeps the existing fence token (the holder
        did not change).
        """
        holder = _require_holder(holder)
        ttl_value = _require_ttl(ttl)
        now_value = float(now)
        with self._lock:
            current = self._read()
            if current is None or current.get("holder") != holder:
                return False
            if now_value >= self._expires_at_of(current):
                return False
            self._write(holder, now_value + ttl_value, self._fence_of(current))
            return True

    def release(self, holder: str) -> bool:
        """Release the lease if ``holder`` is the recorded holder.

        The fence token is preserved across a release so it stays monotonic
        across the whole lease file lifetime. Returns False when the lease is
        free or recorded to a different holder.
        """
        holder = _require_holder(holder)
        with self._lock:
            current = self._read()
            if current is None or current.get("holder") != holder:
                return False
            self._write(None, 0.0, self._fence_of(current))
            return True

    def holder(self, now: float) -> Optional[str]:
        """Return the current holder, or None when the lease is free/expired."""
        now_value = float(now)
        with self._lock:
            current = self._read()
            if current is None:
                return None
            current_holder = current.get("holder")
            if current_holder is None:
                return None
            if now_value >= self._expires_at_of(current):
                return None
            return current_holder

    def is_leader(self, holder: str, now: float) -> bool:
        """Return True when ``holder`` currently holds the lease."""
        return self.holder(now) == holder

    def fence(self) -> int:
        """Return the persisted fencing token (0 when no record exists)."""
        with self._lock:
            return self._fence_of(self._read())


class KeyedQueue:
    """Serialize work per key with an independent lock for each key.

    Calls with the same key run one at a time in submission order; calls with
    different keys may run concurrently. Exceptions from ``fn`` propagate to
    the caller after the per-key lock has been released.
    """

    def __init__(self) -> None:
        self._locks: Dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    def _lock_for(self, key: str) -> threading.Lock:
        with self._guard:
            lock = self._locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._locks[key] = lock
            return lock

    def submit(self, key: str, fn: Callable[[], Any]) -> Any:
        """Run ``fn`` under the lock for ``key`` and return its result.

        Raises ValueError when ``key`` is not a non-empty string. Any exception
        raised by ``fn`` is propagated unchanged once the lock is released.
        """
        if not isinstance(key, str) or not key:
            raise ValueError("key must be a non-empty string")
        if not callable(fn):
            raise ValueError("fn must be callable")
        lock = self._lock_for(key)
        with lock:
            return fn()


class Sweeper:
    """Run a callback no more often than once per interval.

    The first tick always runs. Afterwards the callback runs only when the
    injected ``now`` is at least ``interval`` seconds past the last successful
    run. A skipped tick returns without calling the callback and never raises.
    A callback that raises is captured in the returned dict's ``error`` field
    and does not advance the last-run mark, so the next eligible tick retries.
    """

    def __init__(self, interval: float) -> None:
        try:
            value = float(interval)
        except (TypeError, ValueError):
            raise ValueError("interval must be a number")
        if math.isnan(value) or math.isinf(value) or value < 0.0:
            raise ValueError("interval must be a non-negative finite number")
        self._interval = value
        self._last_run: Optional[float] = None
        self._lock = threading.Lock()

    @property
    def interval(self) -> float:
        """The configured minimum seconds between runs."""
        return self._interval

    def run_once(
        self, fn: Callable[[], Any], now: float
    ) -> Dict[str, Any]:
        """Run ``fn`` when due, returning a status dict.

        The result always contains ``"ran"`` (bool) and ``"at"`` (the supplied
        ``now``). A successful run adds ``"result"``; a raising run adds
        ``"error"`` (the exception instance) and leaves ``last_run`` unchanged.
        """
        if not callable(fn):
            raise ValueError("fn must be callable")
        now_value = float(now)
        with self._lock:
            if self._last_run is not None:
                if (now_value - self._last_run) < self._interval:
                    return {"ran": False, "at": now_value}
            try:
                result = fn()
            except Exception as exc:  # noqa: BLE001 - captured, never re-raised
                return {"ran": False, "at": now_value, "error": exc}
            self._last_run = now_value
            return {"ran": True, "at": now_value, "result": result}

    def last_run(self) -> Optional[float]:
        """Return the ``now`` of the last successful run, or None."""
        with self._lock:
            return self._last_run
