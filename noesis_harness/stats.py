"""noesis_harness/stats.py — basic descriptive statistics.

Patterns: LoopX stats.
Stdlib only.
"""
from __future__ import annotations
from typing import List, Sequence

def mean(xs: Sequence[float]) -> float:
    if not xs: return 0.0
    return sum(xs) / len(xs)
def median(xs: Sequence[float]) -> float:
    if not xs: return 0.0
    s = sorted(xs); n = len(s); mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2
def variance(xs: Sequence[float]) -> float:
    if len(xs) < 2: return 0.0
    m = mean(xs); return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
def stdev(xs: Sequence[float]) -> float:
    return variance(xs) ** 0.5
