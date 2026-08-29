"""noesis_harness/progress_bar.py — simple progress tracker.

Patterns: LoopX progress.
Stdlib only.
"""
from __future__ import annotations

class Progress:
    def __init__(self, total: int):
        if total < 1: raise ValueError("total >=1")
        self._total = total; self._done = 0
    def tick(self) -> float: self._done += 1; return self.done()
    def done(self) -> float: return self._done / self._total
    def remaining(self) -> int: return max(0, self._total - self._done)
    def finished(self) -> bool: return self._done >= self._total
    def __len__(self): return self._done
