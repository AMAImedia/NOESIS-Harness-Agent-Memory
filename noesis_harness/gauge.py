"""noesis_harness/gauge.py — thread-safe gauge.

Patterns: LoopX gauge.
Stdlib only.
"""
from __future__ import annotations
import threading

class Gauge:
    def __init__(self, initial: float = 0.0):
        self._v = float(initial); self._lock = threading.Lock()
    def set(self, v: float) -> None:
        with self._lock: self._v = float(v)
    def inc(self, n: float = 1.0) -> float:
        with self._lock: self._v += n; return self._v
    def dec(self, n: float = 1.0) -> float:
        with self._lock: self._v -= n; return self._v
    def get(self) -> float:
        with self._lock: return self._v
