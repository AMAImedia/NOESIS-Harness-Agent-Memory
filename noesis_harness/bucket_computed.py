"""noesis_harness/bucket_computed.py — bucket computed.

Patterns: LoopX bucket computed.
Stdlib only.
"""
from __future__ import annotations
from typing import Callable, Dict, Any, List

class BucketComputed:
    def __init__(self, capacity: int, compute_fn: Callable = None):
        if capacity < 1: raise ValueError("capacity >=1")
        self._cap = capacity; self._compute = compute_fn; self._data: Dict[str, Any] = {}; self._order: List[str] = []; self._disabled = set()
    def get(self, key: str) -> Any:
        if key in self._disabled: return None
        if key in self._data: return self._data[key]
        if self._compute and len(self._data) < self._cap:
            self._data[key] = self._compute(key); self._order.append(key); return self._data[key]
        return None
    def invalidate(self, key: str) -> bool:
        self._disabled.add(key)
        if key in self._data: del self._data[key]; self._order.remove(key); return True
        return False
    def clear(self) -> int: n = len(self._data); self._data.clear(); self._order.clear(); return n
    def __len__(self): return len(self._data)
    def full(self) -> bool: return len(self._data) >= self._cap
