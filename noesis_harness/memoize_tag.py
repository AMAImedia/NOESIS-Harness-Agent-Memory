"""noesis_harness/memoize_tag.py — tagged memoize (invalidate by tag).

Patterns: LoopX memoize.
Stdlib only.
"""
from __future__ import annotations
from typing import Dict, Callable, Any

class TaggedMemo:
    def __init__(self): self._cache: Dict[str, Any] = {}; self._tags: Dict[str, set] = {}
    def get(self, key: str, tag: str = "default") -> Any:
        return self._cache.get(key)
    def put(self, key: str, value: Any, tag: str = "default") -> None:
        self._cache[key] = value; self._tags.setdefault(tag, set()).add(key)
    def invalidate(self, tag: str) -> int:
        keys = self._tags.pop(tag, set()); removed = 0
        for k in keys:
            if self._cache.pop(k, None) is not None: removed += 1
        return removed
    def clear(self) -> int:
        n = len(self._cache); self._cache.clear(); self._tags.clear(); return n
    def __len__(self): return len(self._cache)
    def __contains__(self, key): return key in self._cache
