"""noesis_harness/stream_parallel.py — parallel stream processing.

Patterns: LoopX stream parallel.
Stdlib only.
"""
from __future__ import annotations
import concurrent.futures
from typing import Iterator, Callable, List

def parallel_stream(fn: Callable, items: Iterator, batch_size: int = 100, max_workers: int = 4) -> list:
    batches = []
    batch = []
    for item in items:
        batch.append(item)
        if len(batch) >= batch_size: batches.append(batch); batch = []
    if batch: batches.append(batch)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        results = list(ex.map(lambda b: [fn(x) for x in b], batches))
    return [item for batch in results for item in batch]
