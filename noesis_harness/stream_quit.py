"""noesis_harness/stream_quit.py — stream quit.

Patterns: LoopX stream quit.
Stdlib only.
"""
from __future__ import annotations
from typing import Iterator, Callable

def stream_quit(fn: Callable, items: Iterator) -> Iterator:
    for item in items: yield fn(item)
def stream_quit_cached(fn: Callable, items: Iterator, cache: dict = None) -> Iterator:
    if cache is None: cache = {}
    for item in items:
        if item not in cache: cache[item] = fn(item)
        yield cache[item]
