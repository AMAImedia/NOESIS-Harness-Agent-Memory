"""noesis_harness/ring_decor.py — ring decorator.

Patterns: LoopX ring decor.
Stdlib only.
"""
from __future__ import annotations
from typing import Callable, Dict, Any, List

class RingDecor:
    def __init__(self, capacity: int):
        if capacity < 1: raise ValueError("capacity >=1")
        self._cap = capacity; self._data: Dict[str, Any] = {}; self._order: List[tuple] = []
    def decor(self, fn: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            if key in self._data: return self._data[key]
            if len(self._data) >= self._cap:
                old = self._order.pop(0); del self._data[old]
            result = fn(*args, **kwargs); self._data[key] = result; self._order.append(key); return result
        return wrapper
    def get(self, key, default=None): return self._data.get(key, default)
    def set(self, key, value) -> None:
        if key not in self._data: self._order.append(key)
        self._data[key] = value
    def invalidate(self, key) -> bool:
        if key in self._data: del self._data[key]; self._order.remove(key); return True
        return False
    def clear(self) -> int: n = len(self._data); self._data.clear(); self._order.clear(); return n
    def __len__(self): return len(self._data)
    def full(self) -> bool: return len(self._data) >= self._cap
