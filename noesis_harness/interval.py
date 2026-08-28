"""noesis_harness/interval.py — interval merge.

Patterns: LoopX interval merge.
Stdlib only.
"""
from __future__ import annotations
from typing import List, Tuple

def merge(intervals: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    if not intervals: return []
    s = sorted(intervals, key=lambda x: x[0])
    out = [list(s[0])]
    for lo, hi in s[1:]:
        if lo <= out[-1][1]:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return [tuple(x) for x in out]
