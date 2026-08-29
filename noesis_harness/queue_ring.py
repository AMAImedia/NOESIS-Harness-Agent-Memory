"""noesis_harness/queue_ring.py — ring queue.

Patterns: LoopX ring queue.
Stdlib only.
"""
from __future__ import annotations

class RingQueue:
    def __init__(self, capacity: int):
        if capacity < 1: raise ValueError("capacity >=1")
        self._buf = [None] * capacity; self._head = 0; self._count = 0; self._cap = capacity
    def push(self, item) -> bool:
        if self._count >= self._cap: return False
        self._buf[(self._head + self._count) % self._cap] = item; self._count += 1; return True
    def pop(self):
        if self._count == 0: return None
        item = self._buf[self._head]; self._head = (self._head + 1) % self._cap; self._count -= 1; return item
    def peek(self): return self._buf[self._head] if self._count > 0 else None
    def __len__(self): return self._count
    def full(self) -> bool: return self._count >= self._cap
    def empty(self) -> bool: return self._count == 0
