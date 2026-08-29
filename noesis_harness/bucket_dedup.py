"""noesis_harness/bucket_dedup.py — bucket dedup.

Patterns: LoopX bucket dedup.
Stdlib only.
"""
from __future__ import annotations

class BucketDedup:
    def __init__(self, capacity: int):
        if capacity < 1: raise ValueError("capacity >=1")
        self._cap = capacity; self._items = []; self._seen = set()
    def add(self, item) -> bool:
        if item in self._seen: return False
        if len(self._items) >= self._cap: return False
        self._items.append(item); self._seen.add(item); return True
    def contains(self, item) -> bool: return item in self._seen
    def __len__(self): return len(self._items)
    def full(self) -> bool: return len(self._items) >= self._cap
    def empty(self) -> bool: return len(self._items) == 0
