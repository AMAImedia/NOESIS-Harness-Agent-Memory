"""noesis_harness/flatten.py — flatten nested lists / dict dot paths.

Patterns: LoopX flatten.
Stdlib only.
"""
from __future__ import annotations

def flat_list(xs):
    out=[]
    for x in xs:
        if isinstance(x, list): out.extend(flat_list(x))
        else: out.append(x)
    return out
def flat_dict(d: dict, prefix="") -> dict:
    out={}
    for k,v in d.items():
        key=f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict): out.update(flat_dict(v, key))
        else: out[key]=v
    return out
