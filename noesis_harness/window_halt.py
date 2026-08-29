"""noesis_harness/window_halt.py — window halt.

Patterns: LoopX window halt.
Stdlib only.
"""
from __future__ import annotations
from collections import deque
from typing import Iterator, Callable

def window_halt(fn: Callable, items: Iterator, size: int = 3) -> Iterator:
    w = deque(maxlen=size)
    for item in items:
        w.append(item)
        if len(w) == size: yield fn(list(w))
