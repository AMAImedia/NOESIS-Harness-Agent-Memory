"""noesis_harness/rate_parallel.py — parallel rate limiter.

Patterns: LoopX rate parallel.
Stdlib only.
"""
from __future__ import annotations
import time
import threading

class RateParallel:
    def __init__(self, limit: int, window: float = 1.0):
        if limit < 1: raise ValueError("limit >=1")
        if window <= 0: raise ValueError("window >0")
        self._limit = limit; self._window = window; self._timestamps = []; self._lock = threading.Lock()
    def allow(self) -> bool:
        with self._lock:
            now = time.monotonic()
            self._timestamps = [t for t in self._timestamps if now - t < self._window]
            if len(self._timestamps) < self._limit: self._timestamps.append(now); return True
            return False
    def count(self) -> int:
        with self._lock: return len(self._timestamps)
    def remaining(self) -> int: return max(0, self._limit - self.count())
