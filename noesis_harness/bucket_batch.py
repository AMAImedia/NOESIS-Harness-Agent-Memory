"""noesis_harness/bucket_batch.py — bucket batch.

Patterns: LoopX bucket batch.
Stdlib only.
"""
from __future__ import annotations

class BucketBatch:
    def __init__(self, capacity: int):
        if capacity < 1: raise ValueError("capacity >=1")
        self._cap = capacity; self._items = []
    def add_batch(self, items: list) -> int:
        space = self._cap - len(self._items); added = items[:space]; self._items.extend(added); return len(added)
    def take_batch(self, n: int) -> list:
        taken = self._items[:n]; self._items = self._items[n:]; return taken
    def __len__(self): return len(self._items)
    def full(self) -> bool: return len(self._items) >= self._cap
    def empty(self) -> bool: return len(self._items) == 0
