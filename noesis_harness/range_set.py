"""noesis_harness/range_set.py — set of integer ranges.

Patterns: LoopX range set.
Stdlib only.
"""
from __future__ import annotations
from typing import List, Tuple

class RangeSet:
    def __init__(self): self._iv: List[Tuple[int, int]] = []
    def add(self, lo: int, hi: int) -> None:
        if lo > hi: lo, hi = hi, lo
        self._iv = merge_with(self._iv + [(lo, hi)])
    def __contains__(self, x: int) -> bool:
        for lo, hi in self._iv:
            if lo <= x <= hi: return True
        return False
    def ranges(self) -> List[Tuple[int, int]]: return list(self._iv)

def merge_with(iv: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    if not iv: return []
    s = sorted(iv, key=lambda x: x[0]); out = [list(s[0])]
    for lo, hi in s[1:]:
        if lo <= out[-1][1]:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return [tuple(x) for x in out]
