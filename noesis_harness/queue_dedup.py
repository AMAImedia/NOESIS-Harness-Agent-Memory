"""noesis_harness/queue_dedup.py — queue dedup.

Patterns: LoopX queue dedup.
Stdlib only.
"""
from __future__ import annotations

class QueueDedup:
    def __init__(self, capacity: int = 0):
        if capacity < 0: raise ValueError("capacity >=0")
        self._cap = capacity; self._items = []; self._seen = set()
    def push(self, item) -> bool:
        if item in self._seen: return False
        if self._cap > 0 and len(self._items) >= self._cap: return False
        self._items.append(item); self._seen.add(item); return True
    def pop(self):
        if not self._items: return None
        item = self._items.pop(0); self._seen.discard(item); return item
    def contains(self, item) -> bool: return item in self._seen
    def __len__(self): return len(self._items)
    def full(self) -> bool: return self._cap > 0 and len(self._items) >= self._cap
    def empty(self) -> bool: return len(self._items) == 0
