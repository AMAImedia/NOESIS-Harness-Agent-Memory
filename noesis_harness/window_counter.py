"""noesis_harness/window_counter.py — sliding window counter.

Patterns: LoopX window counter.
Stdlib only.
"""
from __future__ import annotations
from collections import deque

class WindowCounter:
    def __init__(self, size: int = 10):
        if size < 1: raise ValueError("size >=1")
        self._size = size; self._window = deque(maxlen=size); self._total = 0
    def add(self, value: float) -> None:
        if self._window and len(self._window) == self._size: self._total -= self._window[0]
        self._window.append(value); self._total += value
    def avg(self) -> float: return self._total / len(self._window) if self._window else 0.0
    def total(self) -> float: return self._total
    def count(self) -> int: return len(self._window)
    def __len__(self): return len(self._window)
