"""noesis_harness/limit_counter.py — simple rate limiter counter.

Patterns: LoopX rate limiter.
Stdlib only.
"""
from __future__ import annotations
import time

class LimitCounter:
    def __init__(self, limit: int, window: float = 1.0):
        if limit < 1: raise ValueError("limit >=1")
        if window <= 0: raise ValueError("window >0")
        self._limit = limit; self._window = window; self._count = 0; self._start = time.monotonic()
    def allow(self) -> bool:
        now = time.monotonic()
        if now - self._start >= self._window: self._count = 0; self._start = now
        if self._count < self._limit: self._count += 1; return True
        return False
    def count(self) -> int: return self._count
    def remaining(self) -> int: return max(0, self._limit - self._count)
