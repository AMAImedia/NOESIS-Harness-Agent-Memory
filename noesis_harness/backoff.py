"""Deterministic backoff schedule for retries.

Borrowed patterns from:
- LoopX (deterministic exponential backoff, no random jitter by default).
"""

import math


def schedule(attempt, base=0.1, cap=5.0, factor=2.0):
    """Return the wait seconds for a given retry attempt.

    attempt: 0-based attempt index. attempt=0 yields base.
    base: starting delay in seconds.
    cap: maximum delay in seconds.
    factor: growth multiplier per attempt.

    wait = min(cap, base * factor ** attempt)
    Pure and deterministic; no randomness involved.
    """
    return min(cap, base * (factor ** attempt))


def jitter_none(x):
    """Deterministic jitter: returns the input unchanged.

    Provides a stable no-op jitter hook so callers can pass a uniform
    jitter interface without introducing randomness.
    """
    return x
