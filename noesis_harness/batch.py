"""noesis_harness/batch.py — chunk a list into batches.

Patterns: LoopX batching.
Stdlib only.
"""
from __future__ import annotations
from typing import List, Any

def chunk(items: List[Any], size: int) -> List[List[Any]]:
    if size < 1: raise ValueError("size >=1")
    return [items[i:i+size] for i in range(0, len(items), size)]
