"""noesis_harness/ring_hook.py — ring hook.

Patterns: LoopX ring hook.
Stdlib only.
"""
from __future__ import annotations
from typing import Dict, Any, List

class RingHook:
    def __init__(self, capacity: int):
        if capacity < 1: raise ValueError("capacity >=1")
        self._cap = capacity; self._data: Dict[str, Any] = {}; self._order: List[str] = []
    def hook(self, key: str, value) -> Any:
        if key not in self._data and len(self._data) >= self._cap:
            old = self._order.pop(0); del self._data[old]
        if key not in self._data: self._order.append(key)
        self._data[key] = value; return value
    def get(self, key: str, default=None): return self._data.get(key, default)
    def set(self, key: str, value) -> None:
        if key not in self._data: self._order.append(key)
        self._data[key] = value
    def invalidate(self, key: str) -> bool:
        if key in self._data: del self._data[key]; self._order.remove(key); return True
        return False
    def clear(self) -> int: n = len(self._data); self._data.clear(); self._order.clear(); return n
    def __len__(self): return len(self._data)
    def full(self) -> bool: return len(self._data) >= self._cap
