"""noesis_harness/quantile.py — quantile (linear interpolation).

Patterns: LoopX quantile.
Stdlib only.
"""
from __future__ import annotations
from typing import Sequence

def quantile(xs: Sequence[float], q: float) -> float:
    if not xs: return 0.0
    if not (0.0 <= q <= 1.0): raise ValueError("q in [0,1]")
    s = sorted(xs); n = len(s)
    if n == 1: return s[0]
    pos = q * (n - 1)
    lo = int(pos); hi = min(lo + 1, n - 1); frac = pos - lo
    return s[lo] + (s[hi] - s[lo]) * frac
