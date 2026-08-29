"""noesis_harness/batch_decor.py — batch decorator.

Patterns: LoopX batch decor.
Stdlib only.
"""
from __future__ import annotations
from typing import Callable, Dict, Any, List

class BatchDecor:
    def __init__(self): self._data: Dict[str, Any] = {}
    def decor(self, fn: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            if key not in self._data: self._data[key] = fn(*args, **kwargs)
            return self._data[key]
        return wrapper
    def get(self, key, default=None): return self._data.get(key, default)
    def set(self, key, value) -> None: self._data[key] = value
    def invalidate(self, key) -> bool: return self._data.pop(key, None) is not None
    def clear(self) -> int: n = len(self._data); self._data.clear(); return n
    def __len__(self): return len(self._data)
