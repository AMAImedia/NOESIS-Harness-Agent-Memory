"""noesis_harness/priority_queue.py — deterministic thread-safe priority queue.

Patterns: LoopX scheduling (bounded priority heap with insertion-order tie-break).
Stdlib only.
"""
from __future__ import annotations
import heapq
import itertools
import threading
from typing import Any


class PriorityQueue:
    """FIFO tie-break by insertion order."""
    def __init__(self):
        self._heap = []  # list[tuple[int, int, Any]]
        self._counter = itertools.count()
        self._lock = threading.Lock()

    def push(self, item: Any, priority: int = 0) -> None:
        with self._lock:
            heapq.heappush(self._heap, (priority, next(self._counter), item))

    def pop(self) -> Any:
        with self._lock:
            if not self._heap:
                return None
            return heapq.heappop(self._heap)[2]

    def peek(self) -> Any:
        with self._lock:
            if not self._heap:
                return None
            return self._heap[0][2]

    def __len__(self) -> int:
        with self._lock:
            return len(self._heap)
