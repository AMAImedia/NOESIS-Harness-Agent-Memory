"""noesis_harness/retry_policy.py — deterministic retry policy.

Patterns: LoopX retry with capped backoff.
Stdlib only.
"""
from __future__ import annotations

class RetryPolicy:
    def __init__(self, max_attempts: int = 3, base: float = 0.1, cap: float = 5.0, factor: float = 2.0):
        if max_attempts < 0: raise ValueError("max_attempts >=0")
        self.max_attempts = max_attempts; self.base = base; self.cap = cap; self.factor = factor
    def should_retry(self, attempt: int) -> bool:
        return attempt < self.max_attempts
    def backoff(self, attempt: int) -> float:
        return min(self.cap, self.base * (self.factor ** attempt))
    def total_backoff(self) -> float:
        return sum(self.backoff(a) for a in range(self.max_attempts))
