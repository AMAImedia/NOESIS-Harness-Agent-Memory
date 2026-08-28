"""noesis_harness/debounce.py — deterministic sampling/debounce.

Patterns: LoopX rate sampling (count-based, no real time).
Stdlib only.
"""
from __future__ import annotations

class Debouncer:
    def __init__(self, window: float):
        if window < 0:
            raise ValueError("window must be >=0")
        self.window = window
        self._last = {}  # key -> last emit time

    def should_emit(self, key: str, now: float) -> bool:
        if self.window == 0:
            return True
        last = self._last.get(key)
        if last is None or now - last >= self.window:
            self._last[key] = now
            return True
        return False

    def reset(self, key: str = None) -> None:
        if key is None:
            self._last.clear()
        else:
            self._last.pop(key, None)
