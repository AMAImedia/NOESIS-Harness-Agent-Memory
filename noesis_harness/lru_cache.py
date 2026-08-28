"""noesis_harness/lru_cache.py — LRU cache.

Patterns: LoopX LRU.
Stdlib only.
"""
from __future__ import annotations
from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity: int):
        if capacity < 1: raise ValueError("capacity >=1")
        self.capacity = capacity; self._d = OrderedDict()
    def get(self, key, default=None):
        if key not in self._d: return default
        self._d.move_to_end(key); return self._d[key]
    def put(self, key, value) -> None:
        if key in self._d: self._d.move_to_end(key)
        self._d[key] = value
        while len(self._d) > self.capacity: self._d.popitem(last=False)
    def __len__(self): return len(self._d)
    def __contains__(self, key): return key in self._d
