"""noesis_harness/cron.py — simple cron matcher (5 fields).

Patterns: LoopX cron.
Stdlib only.
"""
from __future__ import annotations
from typing import List

def _match_field(field: str, value: int, maxv: int) -> bool:
    if field == "*": return True
    for part in field.split(","):
        if "/" in part:
            base, step = part.split("/")
            base = 0 if base == "*" else int(base)
            step = int(step)
            if step <= 0: return False
            if base <= value < maxv and (value - base) % step == 0: return True
        else:
            if int(part) == value: return True
    return False

def matches(spec: str, minute: int, hour: int, dom: int, month: int, dow: int) -> bool:
    parts = spec.split()
    if len(parts) != 5: raise ValueError("need 5 fields")
    return (_match_field(parts[0], minute, 60) and _match_field(parts[1], hour, 24)
            and _match_field(parts[2], dom, 32) and _match_field(parts[3], month, 13)
            and _match_field(parts[4], dow, 7))
