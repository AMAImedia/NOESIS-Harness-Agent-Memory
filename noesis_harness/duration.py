"""noesis_harness/duration.py — parse duration strings (e.g. 1h30m).

Patterns: LoopX duration.
Stdlib only.
"""
from __future__ import annotations

_UNITS = {"d": 86400, "h": 3600, "m": 60, "s": 1, "ms": 0.001}

def parse(text: str) -> float:
    text = text.strip()
    if not text: raise ValueError("empty")
    total = 0.0; i = 0; n = len(text)
    while i < n:
        j = i
        while j < n and (text[j].isdigit() or (text[j] == "." and j > i)): j += 1
        num = text[i:j]
        if not num: raise ValueError("bad duration")
        unit = text[j:j+2] if text[j:j+2] in _UNITS else text[j:j+1]
        if unit not in _UNITS: raise ValueError("bad unit")
        total += float(num) * _UNITS[unit]
        i = j + len(unit)
    return total
