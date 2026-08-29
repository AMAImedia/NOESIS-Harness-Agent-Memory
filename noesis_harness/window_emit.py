"""noesis_harness/window_emit.py — window emit.

Patterns: LoopX window emit.
Stdlib only.
"""
from __future__ import annotations
from collections import deque
from typing import Iterator, Callable

def window_emit(fn: Callable, items: Iterator, size: int = 3) -> Iterator:
    w = deque(maxlen=size)
    for item in items:
        w.append(item)
        if len(w) == size: yield fn(list(w))
