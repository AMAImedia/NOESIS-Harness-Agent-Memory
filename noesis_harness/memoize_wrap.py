"""noesis_harness/memoize_wrap.py — wrap memoize.

Patterns: LoopX memoize wrap.
Stdlib only.
"""
from __future__ import annotations
from typing import Dict, Any

class MemoWrap:
    def __init__(self): self._data: Dict[str, Any] = {}
    def wrap(self, key: str, value) -> Any:
        if key not in self._data: self._data[key] = value
        return self._data[key]
    def get(self, key: str, default=None): return self._data.get(key, default)
    def set(self, key: str, value) -> None: self._data[key] = value
    def invalidate(self, key: str) -> bool: return self._data.pop(key, None) is not None
    def clear(self) -> int: n = len(self._data); self._data.clear(); return n
    def __len__(self): return len(self._data)
    def __contains__(self, key): return key in self._data
