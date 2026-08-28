"""noesis_harness/matcher.py — glob-style pattern matcher.

Patterns: LoopX matcher.
Stdlib only.
"""
from __future__ import annotations

def match(pattern: str, text: str) -> bool:
    if pattern == "*": return True
    pi = ti = 0; pstar = -1; tstar = -1
    while ti < len(text):
        if pi < len(pattern) and (pattern[pi] == "?" or pattern[pi] == text[ti]):
            pi += 1; ti += 1
        elif pi < len(pattern) and pattern[pi] == "*":
            pstar = pi; tstar = ti; pi += 1
        elif pstar != -1:
            pi = pstar + 1; ti = tstar + 1; tstar += 1
        else:
            return False
    while pi < len(pattern) and pattern[pi] == "*": pi += 1
    return pi == len(pattern)
