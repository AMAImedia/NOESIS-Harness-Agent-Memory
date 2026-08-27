"""noesis_harness/rate_limiter.py

Deterministic token-bucket rate limiter for agent action throttling.

Pattern adapted from LoopX token-bucket flow control. Stdlib only
(threading, time). The limiter is pure with respect to its clock: every
public method accepts an optional `now` override so behavior is fully
deterministic and testable without sleeping. Storage/recall/coordination
never call an LLM; this module is pure arithmetic over timestamps.

Thread-safety: all mutating state is guarded by a single Lock so concurrent
agents can share one limiter instance.
"""

from __future__ import annotations

import threading
import time


class RateLimiter:
    """Token-bucket rate limiter.

    `capacity` is the maximum number of tokens the bucket can hold.
    `refill_per_sec` is the steady-state refill rate; the bucket regains
    `refill_per_sec` tokens every second, up to `capacity`.

    All methods accept a `now` argument (seconds, float). When omitted the
    real monotonic clock is used. Supplying `now` makes the limiter fully
    deterministic and reproducible in tests.
    """

    def __init__(self, capacity, refill_per_sec):
        self.capacity = float(capacity)
        self.refill_per_sec = float(refill_per_sec)
        self._lock = threading.Lock()
        self._tokens = float(capacity)
        self._last = 0.0

    def _compute_tokens(self, now):
        if now <= self._last:
            return self._tokens
        elapsed = now - self._last
        refilled = elapsed * self.refill_per_sec
        return min(self.capacity, self._tokens + refilled)

    def tokens(self, now=None):
        """Return the current token count (clamped to capacity)."""
        if now is None:
            now = time.monotonic()
        with self._lock:
            return self._compute_tokens(now)

    def allow(self, n=1, now=None):
        """Consume `n` tokens if available; return True on success, False otherwise.

        On success the bucket is refilled to `now` and `n` tokens are removed.
        On failure the bucket state is left untouched (no partial consumption).
        """
        if now is None:
            now = time.monotonic()
        n = int(n)
        with self._lock:
            available = self._compute_tokens(now)
            if available >= n:
                self._tokens = available - n
                self._last = now
                return True
            return False
