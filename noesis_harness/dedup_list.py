"""noesis_harness/dedup_list.py — dedup preserving order.

Patterns: LoopX dedup.
Stdlib only.
"""
from __future__ import annotations

def dedup(xs: list) -> list:
    seen=set(); out=[]
    for x in xs:
        if x not in seen: seen.add(x); out.append(x)
    return out
