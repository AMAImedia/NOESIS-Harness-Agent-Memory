"""noesis_harness/parse_bool.py — bool parsing from text.

Patterns: LoopX parse bool.
Stdlib only.
"""
from __future__ import annotations

_TRUTHY = {"1", "true", "yes", "on", "y", "t"}
_FALSY = {"0", "false", "no", "off", "n", "f"}

def parse_bool(text: str, default: bool = False) -> bool:
    if text is None: return default
    t = str(text).strip().lower()
    if t in _TRUTHY: return True
    if t in _FALSY: return False
    return default
