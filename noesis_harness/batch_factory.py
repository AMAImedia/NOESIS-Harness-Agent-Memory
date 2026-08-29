"""noesis_harness/batch_factory.py — batch factory.

Patterns: LoopX batch factory.
Stdlib only.
"""
from __future__ import annotations
from typing import Callable, Dict, Any, List

class BatchFactory:
    def __init__(self): self._data: Dict[str, Any] = {}; self._factories: Dict[str, Callable] = {}; self._disabled = set()
    def register(self, key: str, factory_fn: Callable) -> None:
        self._factories[key] = factory_fn
    def get_batch(self, keys: List[str]) -> Dict[str, Any]:
        out = {}
        for k in keys:
            if k in self._disabled: continue
            if k not in self._data:
                if k in self._factories: self._data[k] = self._factories[k]()
                else: continue
            out[k] = self._data[k]
        return out
    def invalidate(self, key: str) -> bool:
        self._disabled.add(key)
        return self._data.pop(key, None) is not None
    def clear(self) -> int: n = len(self._data); self._data.clear(); return n
    def __len__(self): return len(self._data)
