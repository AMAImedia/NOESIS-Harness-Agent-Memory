"""noesis_harness/timer.py — deterministic elapsed timer.

Patterns: LoopX timing.
Stdlib only.
"""
from __future__ import annotations
import time

class Timer:
    def __init__(self, start: float = None):
        self.start = start if start is not None else time.perf_counter()
    def elapsed(self, now: float = None) -> float:
        now = now if now is not None else time.perf_counter()
        return max(0.0, now - self.start)
    def reset(self, now: float = None) -> None:
        self.start = now if now is not None else time.perf_counter()
