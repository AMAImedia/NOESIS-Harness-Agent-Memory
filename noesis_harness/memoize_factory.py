"""noesis_harness/memoize_factory.py — factory memoize.

Patterns: LoopX memoize factory.
Stdlib only.
"""
from __future__ import annotations
from typing import Dict, Callable, Any

class MemoFactory:
    def __init__(self): self._data: Dict[str, Any] = {}; self._factories: Dict[str, Callable] = {}; self._disabled = set()
    def register(self, key: str, factory_fn: Callable) -> None:
        self._factories[key] = factory_fn
    def get(self, key: str) -> Any:
        if key in self._disabled: return None
        if key not in self._data:
            if key in self._factories: self._data[key] = self._factories[key]()
            else: return None
        return self._data[key]
    def invalidate(self, key: str) -> bool:
        self._disabled.add(key)
        return self._data.pop(key, None) is not None
    def clear(self) -> int: n = len(self._data); self._data.clear(); return n
    def __len__(self): return len(self._data)
    def __contains__(self, key): return key in self._data or key in self._factories
