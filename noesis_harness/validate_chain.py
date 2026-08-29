"""noesis_harness/validate_chain.py — chained validation.

Patterns: LoopX validation chain.
Stdlib only.
"""
from __future__ import annotations
from typing import Any, List, Callable

class Chain:
    def __init__(self): self._checks: List[Callable] = []
    def add(self, check: Callable) -> "Chain": self._checks.append(check); return self
    def validate(self, value: Any) -> List[str]:
        errors = []
        for fn in self._checks: errors.extend(fn(value))
        return errors
    def __len__(self): return len(self._checks)
