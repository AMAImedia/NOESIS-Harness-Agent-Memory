"""noesis_harness/stream_filter.py — stream filtering.

Patterns: LoopX stream.
Stdlib only.
"""
from __future__ import annotations
from typing import Iterator, Callable, Any

def filter_stream(items: Iterator, predicate: Callable) -> Iterator:
    for item in items:
        if predicate(item): yield item
def take_while(items: Iterator, predicate: Callable) -> Iterator:
    for item in items:
        if not predicate(item): break
        yield item
def drop_while(items: Iterator, predicate: Callable) -> Iterator:
    started = False
    for item in items:
        if not started and predicate(item): continue
        started = True; yield item
