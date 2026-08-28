"""noesis_harness/multimap.py — multimap (key to many values).

Patterns: LoopX multimap.
Stdlib only.
"""
from __future__ import annotations
from collections import defaultdict
from typing import List

class MultiMap:
    def __init__(self): self._m = defaultdict(list)
    def put(self, k, v) -> None: self._m[k].append(v)
    def get(self, k) -> List: return list(self._m.get(k, ()))
    def keys(self): return list(self._m.keys())
    def __contains__(self, k): return k in self._m
