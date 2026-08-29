"""noesis_harness/memoize_deep.py — deep memoize (nested keys).

Patterns: LoopX memoize deep.
Stdlib only.
"""
from __future__ import annotations
from typing import Any

class MemoDeep:
    def __init__(self): self._cache = {}
    def get(self, *keys):
        cur = self._cache
        for k in keys:
            if isinstance(cur, dict) and k in cur: cur = cur[k]
            else: return None
        return cur
    def put(self, value, *keys) -> None:
        cur = self._cache
        for k in keys[:-1]:
            if k not in cur or not isinstance(cur[k], dict): cur[k] = {}
            cur = cur[k]
        cur[keys[-1]] = value
    def invalidate(self, *keys) -> bool:
        cur = self._cache
        for k in keys[:-1]:
            if not isinstance(cur, dict) or k not in cur: return False
            cur = cur[k]
        return cur.pop(keys[-1], None) is not None
    def clear(self) -> int: n = len(str(self._cache)); self._cache.clear(); return n
    def __len__(self): return len(self._cache)
