"""noesis_harness/stats_util.py — additional statistics helpers.

Patterns: LoopX stats.
Stdlib only.
"""
from __future__ import annotations
from typing import Sequence

def percentile(xs: Sequence[float], p: float) -> float:
    if not xs: return 0.0
    s = sorted(xs); k = (len(s) - 1) * p; f = int(k); c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)
def zscore(x: float, xs: Sequence[float]) -> float:
    if len(xs) < 2: return 0.0
    m = sum(xs) / len(xs); std = (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5
    return (x - m) / std if std > 0 else 0.0
def moving_avg(xs: Sequence[float], window: int = 3) -> list:
    if window < 1: raise ValueError("window >=1")
    return [sum(xs[max(0, i - window + 1):i + 1]) / min(i + 1, window) for i in range(len(xs))]
