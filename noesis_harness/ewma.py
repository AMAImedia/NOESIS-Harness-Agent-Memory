"""noesis_harness/ewma.py — exponentially weighted moving average.

Patterns: LoopX EWMA.
Stdlib only.
"""
from __future__ import annotations

class EWMA:
    def __init__(self, alpha: float = 0.3):
        if not (0.0 < alpha <= 1.0): raise ValueError("alpha in (0,1]")
        self.alpha = alpha; self._value = None; self._n = 0
    def update(self, x: float) -> float:
        if self._value is None: self._value = x
        else: self._value = self.alpha * x + (1 - self.alpha) * self._value
        self._n += 1; return self._value
    def value(self) -> float: return self._value
    def count(self) -> int: return self._n
