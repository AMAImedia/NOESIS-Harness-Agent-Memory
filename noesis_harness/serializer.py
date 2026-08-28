"""noesis_harness/serializer.py — safe JSON serializer with fallback.

Patterns: LoopX serializer.
Stdlib only.
"""
from __future__ import annotations
import json
from typing import Any

def to_json(value: Any) -> str:
    return json.dumps(value, default=_fallback, sort_keys=True)
def _fallback(o: Any):
    if isinstance(o, (set, frozenset)): return sorted(o)
    if hasattr(o, "__dict__"): return {k: v for k, v in vars(o).items() if not k.startswith("_")}
    return str(o)
def from_json(text: str) -> Any:
    return json.loads(text)
