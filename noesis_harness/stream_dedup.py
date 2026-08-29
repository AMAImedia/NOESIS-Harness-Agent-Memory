"""noesis_harness/stream_dedup.py — stream dedup.

Patterns: LoopX stream dedup.
Stdlib only.
"""
from __future__ import annotations
from typing import Iterator, Any

def stream_dedup(items: Iterator) -> Iterator:
    seen = set()
    for item in items:
        if item not in seen: seen.add(item); yield item
def stream_dedup_key(items: Iterator, key_fn) -> Iterator:
    seen = set()
    for item in items:
        k = key_fn(item)
        if k not in seen: seen.add(k); yield item
