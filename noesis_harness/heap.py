"""noesis_harness/heap.py — min-heap wrapper.

Patterns: LoopX heap.
Stdlib only.
"""
from __future__ import annotations
import heapq

class MinHeap:
    def __init__(self): self._h = []
    def push(self, item) -> None: heapq.heappush(self._h, item)
    def pop(self):
        return heapq.heappop(self._h) if self._h else None
    def peek(self):
        return self._h[0] if self._h else None
    def __len__(self): return len(self._h)
