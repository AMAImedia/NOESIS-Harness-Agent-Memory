"""noesis_harness/word_wrap.py — greedy word wrap.

Patterns: LoopX word wrap.
Stdlib only.
"""
from __future__ import annotations
from typing import List

def wrap(text: str, width: int) -> List[str]:
    if width < 1: raise ValueError("width >=1")
    words = text.split()
    if not words: return []
    lines: List[str] = []; cur = ""
    for w in words:
        if not cur: cur = w
        elif len(cur) + 1 + len(w) <= width: cur += " " + w
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines
