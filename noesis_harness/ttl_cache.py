"""noesis_harness/ttl_cache.py — TTL cache with explicit clock.

Patterns: LoopX TTL lease (deterministic via now).
Stdlib only.
"""
from __future__ import annotations
import time

class TTLCache:
    def __init__(self, ttl: float = 60.0):
        if ttl <= 0: raise ValueError("ttl >0")
        self.ttl = ttl; self._m = {}
    def put(self, key, value, now: float = None) -> None:
        now = now if now is not None else time.time()
        self._m[key] = (value, now)
    def get(self, key, now: float = None):
        now = now if now is not None else time.time()
        v = self._m.get(key)
        if v is None: return None
        val, at = v
        if now - at >= self.ttl:
            del self._m[key]; return None
        return val
    def __len__(self): return len(self._m)
