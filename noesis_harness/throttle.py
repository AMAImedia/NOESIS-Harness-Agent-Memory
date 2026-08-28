"""noesis_harness/throttle.py — call throttle.

Patterns: LoopX throttle.
Stdlib only.
"""
from __future__ import annotations
import time

class Throttle:
    def __init__(self, interval: float):
        if interval < 0: raise ValueError("interval >=0")
        self.interval = interval; self._last = None
    def allow(self, now: float = None) -> bool:
        now = now if now is not None else time.perf_counter()
        if self._last is None or now - self._last >= self.interval:
            self._last = now; return True
        return False
