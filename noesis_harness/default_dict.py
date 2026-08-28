"""noesis_harness/default_dict.py — default dict wrapper.

Patterns: LoopX default dict.
Stdlib only.
"""
from __future__ import annotations
from collections import defaultdict

class DefaultMap:
    def __init__(self, factory=int):
        self._d = defaultdict(factory)
    def put(self, k, v) -> None: self._d[k] = v
    def get(self, k): return self._d[k]
    def keys(self): return list(self._d.keys())
    def __contains__(self, k): return k in self._d
    def __len__(self): return len(self._d)
