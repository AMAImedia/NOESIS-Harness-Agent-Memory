"""noesis_harness/scheduler.py — simple interval scheduler (in-thread).

Patterns: LoopX scheduler.
Stdlib only.
"""
from __future__ import annotations
from typing import Callable, List

class Scheduler:
    def __init__(self):
        self._tasks: List[tuple] = []
    def every(self, interval: float, fn: Callable[[], None]) -> int:
        if interval <= 0: raise ValueError("interval >0")
        self._tasks.append((interval, fn)); return len(self._tasks)
    def run_pending(self, elapsed: float) -> None:
        for interval, fn in self._tasks:
            if elapsed >= interval: fn()
    def __len__(self): return len(self._tasks)
