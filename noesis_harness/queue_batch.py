"""noesis_harness/queue_batch.py — queue batch.

Patterns: LoopX queue batch.
Stdlib only.
"""
from __future__ import annotations

class QueueBatch:
    def __init__(self, capacity: int):
        if capacity < 1: raise ValueError("capacity >=1")
        self._cap = capacity; self._items = []
    def push_batch(self, items: list) -> int:
        space = self._cap - len(self._items); added = items[:space]; self._items.extend(added); return len(added)
    def pop_batch(self, n: int) -> list:
        taken = self._items[:n]; self._items = self._items[n:]; return taken
    def peek_batch(self, n: int = -1) -> list:
        if n < 0: return list(self._items)
        return self._items[:n]
    def __len__(self): return len(self._items)
    def full(self) -> bool: return len(self._items) >= self._cap
    def empty(self) -> bool: return len(self._items) == 0
