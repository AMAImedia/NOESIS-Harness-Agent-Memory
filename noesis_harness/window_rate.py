"""noesis_harness/window_rate.py — sliding window rate limiter.

Patterns: LoopX rate limiter.
Stdlib only.
"""
from __future__ import annotations
import time

class WindowRate:
    def __init__(self, limit: int, window: float = 1.0):
        if limit < 1: raise ValueError("limit >=1")
        if window <= 0: raise ValueError("window >0")
        self._limit = limit; self._window = window; self._timestamps = []
    def allow(self) -> bool:
        now = time.monotonic()
        self._timestamps = [t for t in self._timestamps if now - t < self._window]
        if len(self._timestamps) < self._limit: self._timestamps.append(now); return True
        return False
    def count(self) -> int: return len(self._timestamps)
    def remaining(self) -> int: return max(0, self._limit - self.count())
