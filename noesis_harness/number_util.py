"""noesis_harness/number_util.py — number helpers.

Patterns: LoopX number util.
Stdlib only.
"""
from __future__ import annotations

def is_even(n: int) -> bool:
    return n % 2 == 0
def is_odd(n: int) -> bool:
    return n % 2 != 0
def clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))
def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t
def is_prime(n: int) -> bool:
    if n < 2: return False
    if n < 4: return True
    if n % 2 == 0 or n % 3 == 0: return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0: return False
        i += 6
    return True
