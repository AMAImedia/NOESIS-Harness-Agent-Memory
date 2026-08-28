"""noesis_harness/bag.py — multiset (bag) counter.

Patterns: LoopX bag.
Stdlib only.
"""
from __future__ import annotations
from collections import defaultdict
from typing import List

class Bag:
    def __init__(self): self._m = defaultdict(int)
    def add(self, item, count: int = 1) -> None:
        if count < 0: raise ValueError("count >=0")
        self._m[item] += count
    def remove(self, item, count: int = 1) -> None:
        if count < 0: raise ValueError("count >=0")
        self._m[item] = max(0, self._m[item] - count)
        if self._m[item] == 0: self._m.pop(item, None)
    def count(self, item) -> int: return self._m.get(item, 0)
    def distinct(self) -> int: return len(self._m)
    def items(self) -> List: return list(self._m.items())
