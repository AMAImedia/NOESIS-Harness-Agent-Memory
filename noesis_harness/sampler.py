"""noesis_harness/sampler.py — weighted sampler.

Patterns: LoopX weighted sampler.
Stdlib only.
"""
from __future__ import annotations
import random
from typing import List, Tuple

class WeightedSampler:
    def __init__(self, seed: int = 0): self._items: List[Tuple[str, float]] = []; self._rng = random.Random(seed)
    def add(self, item: str, weight: float) -> None:
        if weight <= 0: raise ValueError("weight >0")
        self._items.append((item, weight))
    def sample(self) -> str:
        if not self._items: raise ValueError("empty")
        total = sum(w for _, w in self._items)
        r = self._rng.random() * total
        acc = 0.0
        for item, w in self._items:
            acc += w
            if r < acc: return item
        return self._items[-1][0]
    def __len__(self): return len(self._items)
