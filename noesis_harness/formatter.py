"""noesis_harness/formatter.py — text formatting helpers.

Patterns: LoopX formatter.
Stdlib only.
"""
from __future__ import annotations

def truncate(text: str, width: int, suffix: str = "...") -> str:
    if width < 0: raise ValueError("width >=0")
    if len(text) <= width: return text
    if width <= len(suffix): return text[:width]
    return text[:width - len(suffix)] + suffix
def pad(text: str, width: int, align: str = "left") -> str:
    if align not in ("left", "right", "center"): raise ValueError("align invalid")
    if len(text) >= width: return text[:width]
    if align == "left": return text.ljust(width)
    if align == "right": return text.rjust(width)
    return text.center(width)
