"""noesis_harness/queue_parallel.py — parallel queue.

Patterns: LoopX queue parallel.
Stdlib only.
"""
from __future__ import annotations
import threading

class QueueParallel:
    def __init__(self, capacity: int = 0):
        if capacity < 0: raise ValueError("capacity >=0")
        self._cap = capacity; self._items = []; self._lock = threading.Lock()
    def push(self, item) -> bool:
        with self._lock:
            if self._cap > 0 and len(self._items) >= self._cap: return False
            self._items.append(item); return True
    def pop(self):
        with self._lock:
            return self._items.pop(0) if self._items else None
    def peek(self):
        with self._lock: return self._items[0] if self._items else None
    def __len__(self):
        with self._lock: return len(self._items)
    def full(self) -> bool:
        with self._lock: return self._cap > 0 and len(self._items) >= self._cap
    def empty(self) -> bool:
        with self._lock: return len(self._items) == 0
