"""noesis_harness/pipeline.py — composable pipeline.

Patterns: LoopX pipeline.
Stdlib only.
"""
from __future__ import annotations
from typing import Callable, List, Any

class Pipeline:
    def __init__(self, steps: List[Callable] = None):
        self.steps = list(steps) if steps else []
    def add(self, fn: Callable) -> None: self.steps.append(fn)
    def run(self, value: Any) -> Any:
        for fn in self.steps: value = fn(value)
        return value
    def __len__(self): return len(self.steps)
