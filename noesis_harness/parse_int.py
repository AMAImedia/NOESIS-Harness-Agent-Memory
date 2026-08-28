"""noesis_harness/parse_int.py — int parsing with bounds.

Patterns: LoopX parse int.
Stdlib only.
"""
from __future__ import annotations

def parse_int(text: str, default: int = 0, lo=None, hi=None) -> int:
    if text is None or text == "": return default
    try: v = int(text)
    except (ValueError, TypeError): return default
    if lo is not None and v < lo: return lo
    if hi is not None and v > hi: return hi
    return v
