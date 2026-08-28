"""noesis_harness/sliding_window.py — fixed-size sliding window counter.

Patterns: LoopX windowed counter.
Stdlib only.
"""
from __future__ import annotations
from collections import deque

class SlidingWindow:
    def __init__(self, size: int):
        if size < 1: raise ValueError("size >=1")
        self.size = size; self._q = deque()
    def add(self, value) -> None:
        self._q.append(value)
        if len(self._q) > self.size: self._q.popleft()
    def values(self): return list(self._q)
    def avg(self) -> float:
        if not self._q: return 0.0
        return sum(self._q) / len(self._q)
    def __len__(self): return len(self._q)
