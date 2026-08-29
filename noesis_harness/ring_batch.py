"""noesis_harness/ring_batch.py — ring batch.

Patterns: LoopX ring batch.
Stdlib only.
"""
from __future__ import annotations

class RingBatch:
    def __init__(self, capacity: int):
        if capacity < 1: raise ValueError("capacity >=1")
        self._buf = [None] * capacity; self._head = 0; self._count = 0; self._cap = capacity
    def add_batch(self, items: list) -> int:
        added = 0
        for item in items:
            if self._count >= self._cap: break
            self._buf[(self._head + self._count) % self._cap] = item; self._count += 1; added += 1
        return added
    def take_batch(self, n: int) -> list:
        taken = []
        for _ in range(min(n, self._count)):
            taken.append(self._buf[self._head]); self._head = (self._head + 1) % self._cap; self._count -= 1
        return taken
    def __len__(self): return self._count
    def full(self) -> bool: return self._count >= self._cap
    def empty(self) -> bool: return self._count == 0
