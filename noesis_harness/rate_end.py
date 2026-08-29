"""noesis_harness/rate_end.py — rate end.

Patterns: LoopX rate end.
Stdlib only.
"""
from __future__ import annotations
import time
from typing import Dict, Any

class RateEnd:
    def __init__(self, window: float = 1.0):
        if window <= 0: raise ValueError("window >0")
        self._window = window; self._data: Dict[str, Any] = {}; self._timestamps: Dict[str, float] = {}
    def end(self, key: str, value) -> Any:
        now = time.monotonic()
        if key in self._data and now - self._timestamps[key] < self._window: return self._data[key]
        self._data[key] = value; self._timestamps[key] = now; return value
    def get(self, key: str, default=None):
        now = time.monotonic()
        if key in self._data and now - self._timestamps[key] < self._window: return self._data[key]
        return default
    def set(self, key: str, value) -> None:
        self._data[key] = value; self._timestamps[key] = time.monotonic()
    def invalidate(self, key: str) -> bool:
        if key in self._data: del self._data[key]; del self._timestamps[key]; return True
        return False
    def clear(self) -> int: n = len(self._data); self._data.clear(); self._timestamps.clear(); return n
    def __len__(self): return len(self._data)
