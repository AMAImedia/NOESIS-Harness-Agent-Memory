"""noesis_harness/barrier.py — reusable barrier.

Patterns: LoopX barrier.
Stdlib only.
"""
from __future__ import annotations

class Barrier:
    def __init__(self, parties: int):
        if parties < 1: raise ValueError("parties >=1")
        self._parties = parties; self._count = 0
    def wait(self) -> bool:
        self._count += 1
        if self._count >= self._parties:
            self._count = 0; return True
        return False
    def __int__(self): return self._count
