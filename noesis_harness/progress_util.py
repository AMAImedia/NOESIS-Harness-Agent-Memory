"""noesis_harness/progress_util.py — progress tracking utility.

Patterns: LoopX progress.
Stdlib only.
"""
from __future__ import annotations
import time

class ProgressTracker:
    def __init__(self, total: int):
        if total < 1: raise ValueError("total >=1")
        self._total = total; self._done = 0; self._start = time.monotonic()
    def tick(self) -> float: self._done += 1; return self.done()
    def done(self) -> float: return self._done / self._total
    def elapsed(self) -> float: return time.monotonic() - self._start
    def eta(self) -> float:
        if self._done == 0: return 0.0
        elapsed = self.elapsed(); return elapsed * (self._total - self._done) / self._done
    def finished(self) -> bool: return self._done >= self._total
    def __len__(self): return self._done
