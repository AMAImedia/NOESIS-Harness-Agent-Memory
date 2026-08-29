"""noesis_harness/validate_util.py — validation helpers.

Patterns: LoopX validation.
Stdlib only.
"""
from __future__ import annotations
from typing import Any, List, Callable

def required(value: Any, name: str = "field") -> List[str]:
    if value is None or value == "": return [f"{name} is required"]
    return []
def in_range(value: int, lo: int, hi: int, name: str = "field") -> List[str]:
    if not (lo <= value <= hi): return [f"{name} must be {lo}-{hi}"]
    return []
def matches(value: str, pattern: str, name: str = "field") -> List[str]:
    import re
    if not re.match(pattern, value): return [f"{name} doesn't match pattern"]
    return []
def validate_all(value: Any, checks: List[Callable]) -> List[str]:
    errors = []
    for check in checks: errors.extend(check(value))
    return errors
