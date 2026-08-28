"""noesis_harness/size_fmt.py — human-readable byte sizes.

Patterns: LoopX size format.
Stdlib only.
"""
from __future__ import annotations

_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]

def format_bytes(n: int) -> str:
    if n < 0: raise ValueError("n >=0")
    if n < 1024: return f"{n} B"
    size = float(n); i = 0
    while size >= 1024 and i < len(_UNITS) - 1:
        size /= 1024.0; i += 1
    return f"{size:.2f} {_UNITS[i]}"
