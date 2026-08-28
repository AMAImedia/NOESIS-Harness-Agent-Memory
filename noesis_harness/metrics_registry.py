"""noesis_harness/metrics_registry.py — registry of counters.

Patterns: LoopX metrics registry.
Stdlib only.
"""
from __future__ import annotations
from typing import Dict

class MetricsRegistry:
    def __init__(self): self._c: Dict[str, int] = {}
    def inc(self, name: str, by: int = 1) -> int:
        if by < 0: raise ValueError("by >=0")
        self._c[name] = self._c.get(name, 0) + by
        return self._c[name]
    def get(self, name: str) -> int: return self._c.get(name, 0)
    def snapshot(self) -> dict: return dict(self._c)
