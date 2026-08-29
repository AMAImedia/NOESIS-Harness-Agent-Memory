"""noesis_harness/memoize_lru.py — LRU memoize.

Patterns: LoopX memoize LRU.
Stdlib only.
"""
from __future__ import annotations
from collections import OrderedDict

class MemoLRU:
    def __init__(self, capacity: int = 128):
        if capacity < 1: raise ValueError("capacity >=1")
        self._cap = capacity; self._d = OrderedDict()
    def get(self, key):
        if key in self._d: self._d.move_to_end(key); return self._d[key]
        return None
    def put(self, key, value) -> None:
        if key in self._d: self._d.move_to_end(key)
        self._d[key] = value
        while len(self._d) > self._cap: self._d.popitem(last=False)
    def invalidate(self, key) -> bool:
        if key in self._d: del self._d[key]; return True
        return False
    def clear(self) -> int: n = len(self._d); self._d.clear(); return n
    def __len__(self): return len(self._d)
    def __contains__(self, key): return key in self._d
