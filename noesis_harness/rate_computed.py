"""noesis_harness/rate_computed.py — rate computed.

Patterns: LoopX rate computed.
Stdlib only.
"""
from __future__ import annotations
import time
from typing import Callable, Dict, Any

class RateComputed:
    def __init__(self, window: float = 1.0, compute_fn: Callable = None):
        if window <= 0: raise ValueError("window >0")
        self._window = window; self._compute = compute_fn; self._data: Dict[str, Any] = {}; self._timestamps: Dict[str, float] = {}
    def get(self, key: str) -> Any:
        now = time.monotonic()
        if key in self._data:
            if now - self._timestamps[key] < self._window: return self._data[key]
            del self._data[key]; del self._timestamps[key]
        if self._compute:
            self._data[key] = self._compute(key); self._timestamps[key] = now; return self._data[key]
        return None
    def invalidate(self, key: str) -> bool:
        if key in self._data: del self._data[key]; del self._timestamps[key]; return True
        return False
    def clear(self) -> int: n = len(self._data); self._data.clear(); self._timestamps.clear(); return n
    def __len__(self): return len(self._data)
