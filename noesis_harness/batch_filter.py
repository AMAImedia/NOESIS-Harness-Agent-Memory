"""noesis_harness/batch_filter.py — batch filtering.

Patterns: LoopX batch filter.
Stdlib only.
"""
from __future__ import annotations
from typing import Iterator, Callable, List

def batch_filter(items: Iterator, predicate: Callable, batch_size: int = 100) -> Iterator[list]:
    batch = []
    for item in items:
        if predicate(item): batch.append(item)
        if len(batch) >= batch_size: yield batch; batch = []
    if batch: yield batch
def batch_select(items: list, predicate: Callable) -> list:
    return [item for item in items if predicate(item)]
def batch_reject(items: list, predicate: Callable) -> list:
    return [item for item in items if not predicate(item)]
