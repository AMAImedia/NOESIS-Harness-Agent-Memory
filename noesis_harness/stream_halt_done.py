"""noesis_harness/stream_halt_done.py — stream halt_done.

Patterns: LoopX stream halt_done.
Stdlib only.
"""
from __future__ import annotations
from typing import Iterator, Callable

def stream_halt_done(fn: Callable, items: Iterator) -> Iterator:
    for item in items: yield fn(item)
def stream_halt_done_cached(fn: Callable, items: Iterator, cache: dict = None) -> Iterator:
    if cache is None: cache = {}
    for item in items:
        if item not in cache: cache[item] = fn(item)
        yield cache[item]
