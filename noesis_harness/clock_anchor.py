"""noesis_harness/clock_anchor.py — monotonic clock anchor.

Patterns: LoopX clock.
Stdlib only.
"""
from __future__ import annotations
import time

class ClockAnchor:
    def __init__(self): self._t0 = time.perf_counter()
    def elapsed(self) -> float: return time.perf_counter() - self._t0
    def reset(self) -> None: self._t0 = time.perf_counter()
