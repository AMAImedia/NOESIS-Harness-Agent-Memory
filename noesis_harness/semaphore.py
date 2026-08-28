"""noesis_harness/semaphore.py — counting semaphore.

Patterns: LoopX semaphore.
Stdlib only.
"""
from __future__ import annotations

class Semaphore:
    def __init__(self, value: int = 1):
        if value < 0: raise ValueError("value >=0")
        self._value = value
    def acquire(self) -> bool:
        if self._value > 0: self._value -= 1; return True
        return False
    def release(self) -> None:
        self._value += 1
    def __int__(self): return self._value
