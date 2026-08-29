"""noesis_harness/stream_pipe.py — stream pipe.

Patterns: LoopX stream pipe.
Stdlib only.
"""
from __future__ import annotations
from typing import Iterator, Callable

def stream_pipe(fn: Callable, items: Iterator) -> Iterator:
    for item in items: yield fn(item)
def stream_pipe_cached(fn: Callable, items: Iterator, cache: dict = None) -> Iterator:
    if cache is None: cache = {}
    for item in items:
        if item not in cache: cache[item] = fn(item)
        yield cache[item]
