"""noesis_harness/ring_dedup.py — ring dedup.

Patterns: LoopX ring dedup.
Stdlib only.
"""
from __future__ import annotations

class RingDedup:
    def __init__(self, capacity: int):
        if capacity < 1: raise ValueError("capacity >=1")
        self._cap = capacity; self._buf = [None] * capacity; self._head = 0; self._count = 0; self._seen = set()
    def add(self, item) -> bool:
        if item in self._seen: return False
        if self._count >= self._cap:
            old = self._buf[self._head]; self._seen.discard(old)
            self._buf[self._head] = item; self._head = (self._head + 1) % self._cap
        else:
            self._buf[(self._head + self._count) % self._cap] = item; self._count += 1
        self._seen.add(item); return True
    def contains(self, item) -> bool: return item in self._seen
    def __len__(self): return self._count
    def full(self) -> bool: return self._count >= self._cap
    def empty(self) -> bool: return self._count == 0
