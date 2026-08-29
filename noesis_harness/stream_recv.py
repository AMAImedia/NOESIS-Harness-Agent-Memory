"""noesis_harness/stream_recv.py — stream recv.

Patterns: LoopX stream recv.
Stdlib only.
"""
from __future__ import annotations
from typing import Iterator, Callable

def stream_recv(fn: Callable, items: Iterator) -> Iterator:
    for item in items: yield fn(item)
def stream_recv_cached(fn: Callable, items: Iterator, cache: dict = None) -> Iterator:
    if cache is None: cache = {}
    for item in items:
        if item not in cache: cache[item] = fn(item)
        yield cache[item]
