"""noesis_harness/rate_token.py — token bucket rate limiter.

Patterns: LoopX rate limiter.
Stdlib only.
"""
from __future__ import annotations
import time

class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float = 1.0):
        if capacity < 1: raise ValueError("capacity >=1")
        if refill_rate <= 0: raise ValueError("refill_rate >0")
        self._cap = capacity; self._rate = refill_rate; self._tokens = float(capacity); self._last = time.monotonic()
    def allow(self) -> bool:
        self._refill()
        if self._tokens >= 1: self._tokens -= 1; return True
        return False
    def _refill(self):
        now = time.monotonic(); elapsed = now - self._last
        self._tokens = min(self._cap, self._tokens + elapsed * self._rate); self._last = now
    def tokens(self) -> float: self._refill(); return self._tokens
    def __len__(self): return int(self.tokens())
