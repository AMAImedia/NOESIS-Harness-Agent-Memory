"""noesis_harness/timer_wheel.py — timing-wheel scheduler.

Patterns: LoopX timer wheel.
Stdlib only.
"""
from __future__ import annotations
from typing import List, Callable

class TimerWheel:
    def __init__(self, slots: int = 60):
        if slots < 1: raise ValueError("slots >=1")
        self._slots = slots; self._wheel = [[] for _ in range(slots)]
    def add(self, delay: int, fn: Callable) -> None:
        if delay < 0: raise ValueError("delay >=0")
        self._wheel[delay % self._slots].append((delay, fn))
    def tick(self, now: int) -> int:
        slot = now % self._slots
        due = [cb for d, cb in self._wheel[slot] if d <= now]
        self._wheel[slot] = [(d, cb) for d, cb in self._wheel[slot] if d > now]
        for cb in due: cb()
        return len(due)
