"""noesis_harness/window_batch.py — window batch processing.

Patterns: LoopX window batch.
Stdlib only.
"""
from __future__ import annotations
from collections import deque
from typing import Iterator, Callable, List

def window_batch(items: Iterator, size: int = 3, step: int = 1) -> Iterator[list]:
    w = deque(maxlen=size)
    for item in items:
        w.append(item)
        if len(w) == size: yield list(w)
        elif len(w) > step: pass
def sliding_windows(items: list, size: int = 3) -> List[list]:
    return [items[i:i+size] for i in range(len(items) - size + 1)]
