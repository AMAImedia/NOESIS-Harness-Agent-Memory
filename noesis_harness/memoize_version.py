"""noesis_harness/memoize_version.py — versioned memoize.

Patterns: LoopX memoize version.
Stdlib only.
"""
from __future__ import annotations
from typing import Dict, Any, Tuple

class MemoVersion:
    def __init__(self): self._data: Dict[str, Tuple[Any, int]] = {}; self._version = 0
    def get(self, key: str):
        entry = self._data.get(key)
        return entry[0] if entry else None
    def put(self, key: str, value) -> int:
        self._version += 1; self._data[key] = (value, self._version); return self._version
    def version(self, key: str) -> int:
        entry = self._data.get(key)
        return entry[1] if entry else 0
    def invalidate(self, key: str) -> bool:
        return self._data.pop(key, None) is not None
    def clear(self) -> int: n = len(self._data); self._data.clear(); return n
    def __len__(self): return len(self._data)
    def __contains__(self, key): return key in self._data
