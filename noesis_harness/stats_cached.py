"""noesis_harness/stats_cached.py — cached running statistics.

Patterns: LoopX cached stats.
Stdlib only.
"""
from __future__ import annotations

class RunningStats:
    def __init__(self): self._n = 0; self._mean = 0.0; self._m2 = 0.0
    def update(self, x: float) -> None:
        self._n += 1; delta = x - self._mean; self._mean += delta / self._n
        delta2 = x - self._mean; self._m2 += delta * delta2
    def count(self) -> int: return self._n
    def mean(self) -> float: return self._mean if self._n > 0 else 0.0
    def variance(self) -> float: return self._m2 / (self._n - 1) if self._n > 1 else 0.0
    def stdev(self) -> float: return self.variance() ** 0.5
