"""noesis_harness/queue_deque.py — thread-safe deque queue.

Patterns: LoopX queue.
Stdlib only.
"""
from __future__ import annotations
import threading
from collections import deque

class ThreadQueue:
    def __init__(self, maxlen: int = 0):
        self._d = deque(maxlen=maxlen if maxlen > 0 else None)
        self._lock = threading.Lock()
    def push(self, item) -> None:
        with self._lock: self._d.append(item)
    def pop(self):
        with self._lock:
            return self._d.popleft() if self._d else None
    def peek(self):
        with self._lock: return self._d[0] if self._d else None
    def size(self) -> int:
        with self._lock: return len(self._d)
    def to_list(self) -> list:
        with self._lock: return list(self._d)
