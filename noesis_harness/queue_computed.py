"""noesis_harness/queue_computed.py — queue computed.

Patterns: LoopX queue computed.
Stdlib only.
"""
from __future__ import annotations
from typing import Callable, Dict, Any, List

class QueueComputed:
    def __init__(self, capacity: int = 0, compute_fn: Callable = None):
        if capacity < 0: raise ValueError("capacity >=0")
        self._cap = capacity; self._compute = compute_fn; self._data: Dict[str, Any] = {}; self._order: List[str] = []; self._disabled = set()
    def get(self, key: str) -> Any:
        if key in self._disabled: return None
        if key in self._data: return self._data[key]
        if self._compute:
            if self._cap > 0 and len(self._data) >= self._cap:
                old = self._order.pop(0); del self._data[old]
            self._data[key] = self._compute(key); self._order.append(key); return self._data[key]
        return None
    def invalidate(self, key: str) -> bool:
        self._disabled.add(key)
        if key in self._data: del self._data[key]; self._order.remove(key); return True
        return False
    def clear(self) -> int: n = len(self._data); self._data.clear(); self._order.clear(); return n
    def __len__(self): return len(self._data)
    def full(self) -> bool: return self._cap > 0 and len(self._data) >= self._cap
