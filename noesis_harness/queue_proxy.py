"""noesis_harness/queue_proxy.py — queue proxy.

Patterns: LoopX queue proxy.
Stdlib only.
"""
from __future__ import annotations
from typing import Dict, Any, List

class QueueProxy:
    def __init__(self, capacity: int = 0):
        if capacity < 0: raise ValueError("capacity >=0")
        self._cap = capacity; self._data: Dict[str, Any] = {}; self._order: List[str] = []
    def get(self, key: str, default=None): return self._data.get(key, default)
    def set(self, key: str, value) -> bool:
        if key in self._data: self._data[key] = value; return True
        if self._cap > 0 and len(self._data) >= self._cap:
            old = self._order.pop(0); del self._data[old]
        self._data[key] = value; self._order.append(key); return True
    def invalidate(self, key: str) -> bool:
        if key in self._data: del self._data[key]; self._order.remove(key); return True
        return False
    def clear(self) -> int: n = len(self._data); self._data.clear(); self._order.clear(); return n
    def __len__(self): return len(self._data)
    def full(self) -> bool: return self._cap > 0 and len(self._data) >= self._cap
