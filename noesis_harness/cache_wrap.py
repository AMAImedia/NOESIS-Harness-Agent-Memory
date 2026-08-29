"""noesis_harness/cache_wrap.py — simple TTL cache wrapper.

Patterns: LoopX cache.
Stdlib only.
"""
from __future__ import annotations
import time

class TTLCache:
    def __init__(self, ttl: float = 60.0):
        if ttl <= 0: raise ValueError("ttl >0")
        self._ttl = ttl; self._data = {}; self._times = {}
    def get(self, key):
        if key in self._data:
            if time.monotonic() - self._times[key] < self._ttl: return self._data[key]
            del self._data[key]; del self._times[key]
        return None
    def put(self, key, value) -> None:
        self._data[key] = value; self._times[key] = time.monotonic()
    def invalidate(self, key) -> bool:
        if key in self._data: del self._data[key]; del self._times[key]; return True
        return False
    def clear(self) -> int: n = len(self._data); self._data.clear(); self._times.clear(); return n
    def __len__(self): return len(self._data)
