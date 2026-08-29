"""noesis_harness/window_pipe.py — window pipe.

Patterns: LoopX window pipe.
Stdlib only.
"""
from __future__ import annotations
from collections import deque
from typing import Iterator, Callable

def window_pipe(fn: Callable, items: Iterator, size: int = 3) -> Iterator:
    w = deque(maxlen=size)
    for item in items:
        w.append(item)
        if len(w) == size: yield fn(list(w))
