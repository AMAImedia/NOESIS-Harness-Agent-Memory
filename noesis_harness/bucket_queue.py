"""noesis_harness/bucket_queue.py — bucket queue.

Patterns: LoopX bucket queue.
Stdlib only.
"""
from __future__ import annotations

class BucketQueue:
    def __init__(self, capacity: int):
        if capacity < 1: raise ValueError("capacity >=1")
        self._cap = capacity; self._items = []; self._count = 0
    def push(self, item) -> bool:
        if self._count >= self._cap: return False
        self._items.append(item); self._count += 1; return True
    def pop(self):
        if self._count == 0: return None
        item = self._items.pop(0); self._count -= 1; return item
    def peek(self): return self._items[0] if self._items else None
    def __len__(self): return self._count
    def full(self) -> bool: return self._count >= self._cap
    def empty(self) -> bool: return self._count == 0
