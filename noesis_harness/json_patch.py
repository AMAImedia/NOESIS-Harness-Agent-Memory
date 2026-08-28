"""noesis_harness/json_patch.py — simple JSON patch.

Patterns: LoopX patch.
Stdlib only.
"""
from __future__ import annotations
from typing import Any, Dict

def apply_patch(doc: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(doc)
    for k, v in patch.items():
        if v is None:
            out.pop(k, None)
        else:
            out[k] = v
    return out
