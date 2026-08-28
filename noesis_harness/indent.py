"""noesis_harness/indent.py — text indentation helper.

Patterns: LoopX indent.
Stdlib only.
"""
from __future__ import annotations

def indent(text: str, prefix: str = "  ", level: int = 1) -> str:
    if level < 0: raise ValueError("level >=0")
    pad = prefix * level
    return "\n".join(pad + line if line else line for line in text.split("\n"))
