"""noesis_harness/batch_stream.py — batch stream processing.

Patterns: LoopX batch stream.
Stdlib only.
"""
from __future__ import annotations
from typing import Iterator, Callable, List

def batch_process(items: Iterator, fn: Callable, batch_size: int = 100) -> Iterator[list]:
    batch = []
    for item in items:
        batch.append(fn(item))
        if len(batch) >= batch_size: yield batch; batch = []
    if batch: yield batch
def batch_map(fn: Callable, items: list, batch_size: int = 100) -> list:
    return [result for batch in batch_process(iter(items), fn, batch_size) for result in batch]
