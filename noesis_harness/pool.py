"""noesis_harness/pool.py — fixed object pool.

Patterns: LoopX object pool.
Stdlib only.
"""
from __future__ import annotations
from typing import Callable

class Pool:
    def __init__(self, factory: Callable, maxsize: int = 10):
        if maxsize < 1: raise ValueError("maxsize >=1")
        self._factory = factory; self._max = maxsize; self._free = []
    def acquire(self):
        if self._free: return self._free.pop()
        return self._factory()
    def release(self, obj) -> None:
        if len(self._free) < self._max: self._free.append(obj)
    def __len__(self): return len(self._free)
