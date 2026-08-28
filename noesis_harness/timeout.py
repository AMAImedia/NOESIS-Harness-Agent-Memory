"""noesis_harness/timeout.py — deadline helper.

Patterns: LoopX timeout.
Stdlib only.
"""
from __future__ import annotations
import time

class Deadline:
    def __init__(self, seconds: float, now: float = None):
        if seconds < 0: raise ValueError("seconds >=0")
        self.seconds = seconds; self.start = now if now is not None else time.perf_counter()
    def expired(self, now: float = None) -> bool:
        now = now if now is not None else time.perf_counter()
        return now - self.start >= self.seconds
    def remaining(self, now: float = None) -> float:
        now = now if now is not None else time.perf_counter()
        return max(0.0, self.seconds - (now - self.start))
