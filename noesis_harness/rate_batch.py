"""noesis_harness/rate_batch.py — batch rate limiter.

Patterns: LoopX rate limiter.
Stdlib only.
"""
from __future__ import annotations
import time

class RateBatch:
    def __init__(self, limit: int, window: float = 1.0):
        if limit < 1: raise ValueError("limit >=1")
        if window <= 0: raise ValueError("window >0")
        self._limit = limit; self._window = window; self._timestamps = []
    def allow_batch(self, n: int) -> int:
        now = time.monotonic()
        self._timestamps = [t for t in self._timestamps if now - t < self._window]
        space = self._limit - len(self._timestamps)
        allowed = min(n, space)
        self._timestamps.extend([now] * allowed)
        return allowed
    def count(self) -> int: return len(self._timestamps)
    def remaining(self) -> int: return max(0, self._limit - self.count())
