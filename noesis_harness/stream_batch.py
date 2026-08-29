"""noesis_harness/stream_batch.py — stream batching.

Patterns: LoopX stream batch.
Stdlib only.
"""
from __future__ import annotations
from typing import Iterator, Callable

def stream_batch(items: Iterator, batch_size: int = 100) -> Iterator[list]:
    batch = []
    for item in items:
        batch.append(item)
        if len(batch) >= batch_size: yield batch; batch = []
    if batch: yield batch
def stream_chunk(items: Iterator, size: int) -> Iterator[list]:
    return stream_batch(items, size)
