"""noesis_harness/json_merge.py — deep merge dicts (right wins).

Patterns: LoopX merge.
Stdlib only.
"""
from __future__ import annotations

def merge(a: dict, b: dict) -> dict:
    out=dict(a)
    for k,v in b.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k]=merge(out[k], v)
        else:
            out[k]=v
    return out
