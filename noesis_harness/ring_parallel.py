"""noesis_harness/ring_parallel.py — parallel ring buffer.

Patterns: LoopX ring parallel.
Stdlib only.
"""
from __future__ import annotations
import threading

class RingParallel:
    def __init__(self, capacity: int):
        if capacity < 1: raise ValueError("capacity >=1")
        self._buf = [None] * capacity; self._head = 0; self._count = 0; self._cap = capacity; self._lock = threading.Lock()
    def push(self, item) -> bool:
        with self._lock:
            if self._count >= self._cap: return False
            self._buf[(self._head + self._count) % self._cap] = item; self._count += 1; return True
    def pop(self):
        with self._lock:
            if self._count == 0: return None
            item = self._buf[self._head]; self._head = (self._head + 1) % self._cap; self._count -= 1; return item
    def __len__(self):
        with self._lock: return self._count
    def full(self) -> bool:
        with self._lock: return self._count >= self._cap
    def empty(self) -> bool:
        with self._lock: return self._count == 0
