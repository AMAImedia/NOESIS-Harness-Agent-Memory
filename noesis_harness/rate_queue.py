"""noesis_harness/rate_queue.py — rate-limited queue.

Patterns: LoopX rate queue.
Stdlib only.
"""
from __future__ import annotations
import time

class RateQueue:
    def __init__(self, limit: int, window: float = 1.0):
        if limit < 1: raise ValueError("limit >=1")
        if window <= 0: raise ValueError("window >0")
        self._limit = limit; self._window = window; self._queue = []; self._timestamps = []
    def push(self, item) -> bool:
        now = time.monotonic()
        self._timestamps = [t for t in self._timestamps if now - t < self._window]
        if len(self._timestamps) < self._limit: self._queue.append(item); self._timestamps.append(now); return True
        return False
    def pop(self): return self._queue.pop(0) if self._queue else None
    def peek(self): return self._queue[0] if self._queue else None
    def __len__(self): return len(self._queue)
    def full(self) -> bool: return len(self._timestamps) >= self._limit
    def empty(self) -> bool: return len(self._queue) == 0
