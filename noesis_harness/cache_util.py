"""noesis_harness/cache_util.py — caching utilities.

Patterns: LoopX cache.
Stdlib only.
"""
from __future__ import annotations
from typing import Any, Dict

class CacheUtil:
    def __init__(self, maxsize: int = 128):
        if maxsize < 1: raise ValueError("maxsize >=1")
        self._data: Dict[str, Any] = {}; self._max = maxsize; self._order = []
    def get(self, key: str, default=None): return self._data.get(key, default)
    def put(self, key: str, value: Any) -> None:
        if key in self._data: self._order.remove(key)
        elif len(self._data) >= self._max:
            old = self._order.pop(0); del self._data[old]
        self._data[key] = value; self._order.append(key)
    def invalidate(self, key: str) -> bool:
        if key in self._data: del self._data[key]; self._order.remove(key); return True
        return False
    def clear(self) -> int: n = len(self._data); self._data.clear(); self._order.clear(); return n
    def __len__(self): return len(self._data)
    def __contains__(self, key): return key in self._data
