"""noesis_harness/rate_dedup.py — rate dedup.

Patterns: LoopX rate dedup.
Stdlib only.
"""
from __future__ import annotations
import time

class RateDedup:
    def __init__(self, window: float = 1.0):
        if window <= 0: raise ValueError("window >0")
        self._window = window; self._seen = {}; self._timestamps = []
    def check(self, key: str) -> bool:
        now = time.monotonic()
        self._timestamps = [(k, t) for k, t in self._timestamps if now - t < self._window]
        self._seen = {k: t for k, t in self._timestamps}
        if key in self._seen: return False
        self._seen[key] = now; self._timestamps.append((key, now)); return True
    def count(self) -> int: return len(self._timestamps)
    def clear(self) -> int: n = len(self._seen); self._seen.clear(); self._timestamps.clear(); return n
    def __len__(self): return len(self._seen)
