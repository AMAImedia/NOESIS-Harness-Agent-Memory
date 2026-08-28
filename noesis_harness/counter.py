"""noesis_harness/counter.py — deterministic thread-safe counter.

Patterns: LoopX counter.
Stdlib only.
"""
from __future__ import annotations
import threading

class Counter:
    def __init__(self, initial: int = 0):
        self._v = initial; self._lock = threading.Lock()
    def inc(self, n: int = 1) -> int:
        with self._lock: self._v += n; return self._v
    def dec(self, n: int = 1) -> int:
        with self._lock: self._v -= n; return self._v
    def get(self) -> int:
        with self._lock: return self._v
    def reset(self) -> None:
        with self._lock: self._v = 0
