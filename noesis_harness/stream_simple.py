"""noesis_harness/stream_simple.py — stream simple.

Patterns: LoopX stream simple.
Stdlib only.
"""
from __future__ import annotations
from typing import Iterator, Callable

def stream_simple(fn: Callable, items: Iterator) -> Iterator:
    for item in items: yield fn(item)
def stream_simple_cached(fn: Callable, items: Iterator, cache: dict = None) -> Iterator:
    if cache is None: cache = {}
    for item in items:
        if item not in cache: cache[item] = fn(item)
        yield cache[item]
