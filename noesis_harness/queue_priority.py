"""noesis_harness/queue_priority.py — priority queue.

Patterns: LoopX priority queue.
Stdlib only.
"""
from __future__ import annotations
import heapq

class PriorityQueue:
    def __init__(self): self._heap = []; self._count = 0
    def push(self, item, priority: int = 0) -> None:
        heapq.heappush(self._heap, (priority, self._count, item)); self._count += 1
    def pop(self): return heapq.heappop(self._heap)[2] if self._heap else None
    def peek(self): return self._heap[0][2] if self._heap else None
    def __len__(self): return len(self._heap)
    def empty(self) -> bool: return len(self._heap) == 0
