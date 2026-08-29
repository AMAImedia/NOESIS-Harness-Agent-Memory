"""noesis_harness/bucket_bind.py — bucket bind.

Patterns: LoopX bucket bind.
Stdlib only.
"""
from __future__ import annotations
from typing import Dict, Any, List

class BucketBind:
    def __init__(self, capacity: int):
        if capacity < 1: raise ValueError("capacity >=1")
        self._cap = capacity; self._data: Dict[str, Any] = {}; self._order: List[str] = []
    def binding(self, key: str, value) -> Any:
        if key in self._data: self._data[key] = value; return value
        if len(self._data) >= self._cap: return None
        self._data[key] = value; self._order.append(key); return value
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
