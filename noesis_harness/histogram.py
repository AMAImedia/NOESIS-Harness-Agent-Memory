"""noesis_harness/histogram.py — simple deterministic histogram.

Patterns: LoopX metrics.
Stdlib only.
"""
from __future__ import annotations
from typing import List, Dict

class Histogram:
    def __init__(self, buckets: List[float]):
        self.buckets = sorted(buckets); self.counts = [0] * (len(self.buckets) + 1); self.total = 0
    def observe(self, value: float) -> None:
        self.total += 1
        for i, b in enumerate(self.buckets):
            if value <= b:
                self.counts[i] += 1; return
        self.counts[-1] += 1
    def to_dict(self) -> Dict:
        return {"buckets": self.buckets, "counts": list(self.counts), "total": self.total}
