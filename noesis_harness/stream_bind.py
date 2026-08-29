"""noesis_harness/stream_bind.py — stream bind.

Patterns: LoopX stream bind.
Stdlib only.
"""
from __future__ import annotations
from typing import Iterator, Callable

def stream_bind(fn: Callable, items: Iterator) -> Iterator:
    for item in items: yield fn(item)
def stream_bind_cached(fn: Callable, items: Iterator, cache: dict = None) -> Iterator:
    if cache is None: cache = {}
    for item in items:
        if item not in cache: cache[item] = fn(item)
        yield cache[item]
