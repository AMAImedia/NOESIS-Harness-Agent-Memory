"""noesis_harness/stream_computed.py — stream computed.

Patterns: LoopX stream computed.
Stdlib only.
"""
from __future__ import annotations
from typing import Iterator, Callable, Dict, Any

def stream_computed(fn: Callable, items: Iterator) -> Iterator:
    for item in items: yield fn(item)
def stream_cached(fn: Callable, items: Iterator, cache: Dict = None) -> Iterator:
    if cache is None: cache = {}
    for item in items:
        if item not in cache: cache[item] = fn(item)
        yield cache[item]
