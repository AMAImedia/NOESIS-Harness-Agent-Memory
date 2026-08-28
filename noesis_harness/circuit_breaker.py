"""noesis_harness/circuit_breaker.py — pure circuit breaker.

Patterns: LoopX resilience (closed/open/half-open by count+time).
Stdlib only.
"""
from __future__ import annotations

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, reset_after: float = 30.0):
        if failure_threshold < 1: raise ValueError("threshold >=1")
        self.failure_threshold = failure_threshold
        self.reset_after = reset_after
        self._failures = 0
        self._opened_at = None
        self._state = "closed"

    def record_failure(self, now: float = 0) -> None:
        if self._state == "open" and self._opened_at is not None and now - self._opened_at >= self.reset_after:
            self._state = "half-open"; self._failures = 0; self._opened_at = None
        if self._state == "half-open":
            self._state = "open"; self._opened_at = now; self._failures = self.failure_threshold
            return
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._state = "open"; self._opened_at = now

    def record_success(self, now: float = 0) -> None:
        if self._state == "open" and self._opened_at is not None and now - self._opened_at >= self.reset_after:
            self._state = "half-open"; self._failures = 0; self._opened_at = None
        if self._state == "half-open":
            self._state = "closed"
        self._failures = 0

    def state(self, now: float = 0) -> str:
        if self._state == "open" and self._opened_at is not None and now - self._opened_at >= self.reset_after:
            return "half-open"
        return self._state
