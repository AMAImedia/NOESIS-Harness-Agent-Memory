"""noesis_harness/cache_tag.py — tag-aware cache.

Patterns: LoopX tagged cache.
Stdlib only.
"""
from __future__ import annotations
from typing import Dict, Any, Set

class TagCache:
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._tags: Dict[str, Set[str]] = {}
    def put(self, key: str, value: Any, tags=None) -> None:
        self._data[key] = value
        if tags:
            for t in tags:
                self._tags.setdefault(t, set()).add(key)
    def get(self, key: str):
        return self._data.get(key)
    def invalidate(self, tag: str) -> int:
        keys = self._tags.pop(tag, set())
        for k in keys: self._data.pop(k, None)
        return len(keys)
    def __len__(self): return len(self._data)
