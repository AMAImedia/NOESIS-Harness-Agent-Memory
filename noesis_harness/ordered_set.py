"""noesis_harness/ordered_set.py — deterministic insertion-order set.

Patterns: LoopX ordered collection.
Stdlib only.
"""
from __future__ import annotations

class OrderedSet:
    def __init__(self, iterable=None):
        self._d = {}
        if iterable:
            for x in iterable: self._d[x] = None
    def add(self, item) -> bool:
        if item in self._d: return False
        self._d[item] = None; return True
    def discard(self, item) -> bool:
        if item in self._d: del self._d[item]; return True
        return False
    def __contains__(self, item): return item in self._d
    def __len__(self): return len(self._d)
    def to_list(self): return list(self._d.keys())
