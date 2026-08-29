"""noesis_harness/list_util.py — list helpers.

Patterns: LoopX list util.
Stdlib only.
"""
from __future__ import annotations
from typing import List, Any

def flatten(xs: list) -> list:
    out = []
    for x in xs:
        if isinstance(x, list): out.extend(flatten(x))
        else: out.append(x)
    return out
def unique(xs: list) -> list:
    seen = set(); out = []
    for x in xs:
        if x not in seen: seen.add(x); out.append(x)
    return out
def compact(xs: list) -> list:
    return [x for x in xs if x is not None and x != "" and x != 0]
def chunk(xs: list, size: int) -> list:
    return [xs[i:i+size] for i in range(0, len(xs), size)]
def first(xs: list, default=None):
    return xs[0] if xs else default
def last(xs: list, default=None):
    return xs[-1] if xs else default
