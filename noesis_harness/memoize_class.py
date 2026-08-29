"""noesis_harness/memoize_class.py — class-based memoize.

Patterns: LoopX memoize.
Stdlib only.
"""
from __future__ import annotations
from typing import Any, Dict

class Memoizer:
    def __init__(self): self._cache: Dict[str, Any] = {}
    def get_or_compute(self, key: str, compute_fn) -> Any:
        if key not in self._cache: self._cache[key] = compute_fn()
        return self._cache[key]
    def invalidate(self, key: str) -> bool:
        return self._cache.pop(key, None) is not None
    def clear(self) -> int: n = len(self._cache); self._cache.clear(); return n
    def __len__(self): return len(self._cache)
    def __contains__(self, key): return key in self._cache
