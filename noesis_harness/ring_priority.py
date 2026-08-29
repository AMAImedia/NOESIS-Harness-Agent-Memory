"""noesis_harness/ring_priority.py — ring priority queue.

Patterns: LoopX ring priority.
Stdlib only.
"""
from __future__ import annotations
import heapq

class RingPriority:
    def __init__(self, capacity: int):
        if capacity < 1: raise ValueError("capacity >=1")
        self._cap = capacity; self._heap = []; self._count = 0
    def push(self, item, priority: int = 0) -> bool:
        if self._count >= self._cap: return False
        heapq.heappush(self._heap, (priority, self._count, item)); self._count += 1; return True
    def pop(self):
        if not self._heap: return None
        return heapq.heappop(self._heap)[2]
    def peek(self): return self._heap[0][2] if self._heap else None
    def __len__(self): return len(self._heap)
    def full(self) -> bool: return len(self._heap) >= self._cap
    def empty(self) -> bool: return len(self._heap) == 0
