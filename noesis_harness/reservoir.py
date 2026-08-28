"""noesis_harness/reservoir.py — reservoir sampling (Algorithm R).

Patterns: LoopX reservoir sampling.
Stdlib only.
"""
from __future__ import annotations
import random
from typing import List, Any

def sample(stream: List[Any], k: int, seed: int = 0) -> List[Any]:
    if k < 1: raise ValueError("k >=1")
    r = random.Random(seed)
    reservoir: List[Any] = []
    for i, item in enumerate(stream):
        if len(reservoir) < k:
            reservoir.append(item)
        else:
            j = r.randint(0, i)
            if j < k: reservoir[j] = item
    return reservoir
