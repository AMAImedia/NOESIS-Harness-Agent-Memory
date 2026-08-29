"""noesis_harness/compact_util.py — remove None / empty.

Patterns: LoopX compact.
Stdlib only.
"""
from __future__ import annotations

def compact(d: dict) -> dict:
    return {k:v for k,v in d.items() if v is not None}
def compact_list(xs: list) -> list:
    return [x for x in xs if x is not None]
