"""noesis_harness/memoize_computed.py — computed memoize.

Patterns: LoopX memoize computed.
Stdlib only.
"""
from __future__ import annotations
from typing import Dict, Callable, Any

class MemoComputed:
    def __init__(self): self._data: Dict[str, Any] = {}; self._fns: Dict[str, Callable] = {}; self._disabled = set()
    def register(self, key: str, compute_fn: Callable) -> None:
        self._fns[key] = compute_fn
    def get(self, key: str) -> Any:
        if key in self._disabled: return None
        if key in self._data: return self._data[key]
        if key in self._fns:
            self._data[key] = self._fns[key](); return self._data[key]
        return None
    def invalidate(self, key: str) -> bool:
        self._disabled.add(key)
        return self._data.pop(key, None) is not None
    def clear(self) -> int: n = len(self._data); self._data.clear(); return n
    def __len__(self): return len(self._data)
    def __contains__(self, key): return key in self._data or key in self._fns
