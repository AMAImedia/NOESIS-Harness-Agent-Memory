"""noesis_harness/counter_map.py — counting map.

Patterns: LoopX counter map.
Stdlib only.
"""
from __future__ import annotations
from collections import defaultdict

class CounterMap:
    def __init__(self): self._m = defaultdict(int)
    def inc(self, key, by: int = 1) -> int:
        if by < 0: raise ValueError("by >=0")
        self._m[key] += by; return self._m[key]
    def get(self, key) -> int: return self._m.get(key, 0)
    def __contains__(self, key): return key in self._m
    def items(self): return list(self._m.items())
