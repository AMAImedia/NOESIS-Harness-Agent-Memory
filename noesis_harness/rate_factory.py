"""noesis_harness/rate_factory.py — rate factory.

Patterns: LoopX rate factory.
Stdlib only.
"""
from __future__ import annotations
import time
from typing import Callable, Dict, Any

class RateFactory:
    def __init__(self, window: float = 1.0, factory_fn: Callable = None):
        if window <= 0: raise ValueError("window >0")
        self._window = window; self._factory = factory_fn; self._data: Dict[str, Any] = {}; self._timestamps: Dict[str, float] = {}; self._disabled = set()
    def get(self, key: str) -> Any:
        if key in self._disabled: return None
        now = time.monotonic()
        if key in self._data:
            if now - self._timestamps[key] < self._window: return self._data[key]
            del self._data[key]; del self._timestamps[key]
        if self._factory:
            self._data[key] = self._factory(key); self._timestamps[key] = now; return self._data[key]
        return None
    def invalidate(self, key: str) -> bool:
        self._disabled.add(key)
        if key in self._data: del self._data[key]; del self._timestamps[key]; return True
        return False
    def clear(self) -> int: n = len(self._data); self._data.clear(); self._timestamps.clear(); return n
    def __len__(self): return len(self._data)
