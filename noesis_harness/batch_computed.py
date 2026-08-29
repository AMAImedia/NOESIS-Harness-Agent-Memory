"""noesis_harness/batch_computed.py — batch computed.

Patterns: LoopX batch computed.
Stdlib only.
"""
from __future__ import annotations
from typing import Callable, Dict, List, Any

class BatchComputed:
    def __init__(self): self._data: Dict[str, Any] = {}; self._fns: Dict[str, Callable] = {}; self._disabled = set()
    def register(self, key: str, compute_fn: Callable) -> None:
        self._fns[key] = compute_fn
    def get_batch(self, keys: List[str]) -> Dict[str, Any]:
        out = {}
        for k in keys:
            if k in self._disabled: continue
            if k in self._data: out[k] = self._data[k]
            elif k in self._fns: self._data[k] = self._fns[k](); out[k] = self._data[k]
        return out
    def invalidate(self, key: str) -> bool:
        self._disabled.add(key)
        return self._data.pop(key, None) is not None
    def clear(self) -> int: n = len(self._data); self._data.clear(); return n
    def __len__(self): return len(self._data)
