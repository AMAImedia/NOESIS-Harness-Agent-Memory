"""noesis_harness/hist_linear.py — fixed-bucket linear histogram.

Patterns: LoopX linear histogram.
Stdlib only.
"""
from __future__ import annotations
from typing import List

class LinearHist:
    def __init__(self, lo: float, hi: float, bins: int):
        if bins < 1: raise ValueError("bins >=1")
        if hi <= lo: raise ValueError("hi > lo")
        self.lo = lo; self.hi = hi; self.bins = bins; self._counts = [0] * bins
    def _idx(self, x: float) -> int:
        if x < self.lo: return 0
        if x >= self.hi: return self.bins - 1
        return int((x - self.lo) / (self.hi - self.lo) * self.bins)
    def record(self, x: float) -> None: self._counts[self._idx(x)] += 1
    def counts(self) -> List[int]: return list(self._counts)
    def total(self) -> int: return sum(self._counts)
