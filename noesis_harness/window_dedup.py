"""noesis_harness/window_dedup.py — window dedup.

Patterns: LoopX window dedup.
Stdlib only.
"""
from __future__ import annotations
from collections import deque
from typing import Iterator, Any

def window_dedup(items: Iterator, size: int = 3) -> Iterator:
    seen = deque(maxlen=size)
    for item in items:
        if item not in seen: seen.append(item); yield item
