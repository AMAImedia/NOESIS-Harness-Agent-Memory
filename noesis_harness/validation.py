"""noesis_harness/validation.py — validation helpers.

Patterns: LoopX validation.
Stdlib only.
"""
from __future__ import annotations
from typing import Any, List

def is_nonempty_str(v: Any) -> bool: return isinstance(v, str) and len(v.strip()) > 0
def is_positive_int(v: Any) -> bool: return isinstance(v, int) and v > 0
def validate(data: dict, rules: dict) -> List[str]:
    errs = []
    for k, fn in rules.items():
        if not fn(data.get(k)): errs.append(k)
    return errs
