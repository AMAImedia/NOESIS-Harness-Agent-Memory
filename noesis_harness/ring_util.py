"""noesis_harness/ring_util.py — ring buffer utility.

Patterns: LoopX ring.
Stdlib only.
"""
from __future__ import annotations

class RingBuf:
    def __init__(self, size: int):
        if size < 1: raise ValueError("size >=1")
        self._buf = [None] * size; self._head = 0; self._count = 0
    def push(self, item) -> None:
        self._buf[(self._head + self._count) % len(self._buf)] = item
        if self._count < len(self._buf): self._count += 1
        else: self._head = (self._head + 1) % len(self._buf)
    def get(self, idx: int):
        if idx < 0 or idx >= self._count: raise IndexError("out of range")
        return self._buf[(self._head + idx) % len(self._buf)]
    def __len__(self): return self._count
    def to_list(self) -> list:
        return [self.get(i) for i in range(self._count)]
