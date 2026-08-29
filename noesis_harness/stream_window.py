"""noesis_harness/stream_window.py — stream window aggregation.

Patterns: LoopX stream window.
Stdlib only.
"""
from __future__ import annotations
from collections import deque
from typing import Iterator, Callable, Any

def window_sum(items: Iterator[float], size: int = 3) -> Iterator[float]:
    w = deque(maxlen=size); total = 0.0
    for item in items:
        if len(w) == size: total -= w[0]
        w.append(item); total += item
        if len(w) == size: yield total
def window_avg(items: Iterator[float], size: int = 3) -> Iterator[float]:
    w = deque(maxlen=size); total = 0.0
    for item in items:
        if len(w) == size: total -= w[0]
        w.append(item); total += item
        if len(w) == size: yield total / size
