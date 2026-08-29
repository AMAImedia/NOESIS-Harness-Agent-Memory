"""noesis_harness/bucket_parallel.py — parallel bucket.

Patterns: LoopX bucket parallel.
Stdlib only.
"""
from __future__ import annotations
import threading

class BucketParallel:
    def __init__(self, capacity: int):
        if capacity < 1: raise ValueError("capacity >=1")
        self._cap = capacity; self._tokens = 0; self._lock = threading.Lock()
    def acquire(self) -> bool:
        with self._lock:
            if self._tokens < self._cap: self._tokens += 1; return True
            return False
    def release(self) -> None:
        with self._lock:
            if self._tokens > 0: self._tokens -= 1
    def tokens(self) -> int:
        with self._lock: return self._tokens
    def free(self) -> int:
        with self._lock: return self._cap - self._tokens
    def __len__(self):
        with self._lock: return self._tokens
