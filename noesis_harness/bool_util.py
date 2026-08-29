"""noesis_harness/bool_util.py — boolean helpers.

Patterns: LoopX bool util.
Stdlib only.
"""
from __future__ import annotations

def to_bool(value) -> bool:
    if isinstance(value, bool): return value
    if isinstance(value, str): return value.strip().lower() in ("1", "true", "yes", "on")
    if isinstance(value, (int, float)): return value != 0
    return bool(value)
def negate(value: bool) -> bool:
    return not value
def all_true(values: list) -> bool:
    return all(values)
def any_true(values: list) -> bool:
    return any(values)
