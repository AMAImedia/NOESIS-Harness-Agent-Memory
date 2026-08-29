"""noesis_harness/rate_decor.py — rate decorator.

Patterns: LoopX rate decor.
Stdlib only.
"""
from __future__ import annotations
import time
from typing import Dict, Any, Callable

class RateDecor:
    def __init__(self, window: float = 1.0):
        if window <= 0: raise ValueError("window >0")
        self._window = window; self._data: Dict[str, Any] = {}; self._timestamps: Dict[str, float] = {}
    def decor(self, fn: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = time.monotonic()
            if key in self._data and now - self._timestamps[key] < self._window: return self._data[key]
            result = fn(*args, **kwargs); self._data[key] = result; self._timestamps[key] = now; return result
        return wrapper
    def get(self, key, default=None):
        now = time.monotonic()
        if key in self._data and now - self._timestamps[key] < self._window: return self._data[key]
        return default
    def set(self, key, value) -> None:
        self._data[key] = value; self._timestamps[key] = time.monotonic()
    def invalidate(self, key) -> bool:
        if key in self._data: del self._data[key]; del self._timestamps[key]; return True
        return False
    def clear(self) -> int: n = len(self._data); self._data.clear(); self._timestamps.clear(); return n
    def __len__(self): return len(self._data)
