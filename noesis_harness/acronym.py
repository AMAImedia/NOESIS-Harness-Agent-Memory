"""noesis_harness/acronym.py — build acronym from words.

Patterns: LoopX acronym.
Stdlib only.
"""
from __future__ import annotations

def acronym(text: str, max_len: int = 0) -> str:
    words = [w for w in text.replace("-", " ").split() if w]
    if not words: return ""
    letters = "".join(w[0].upper() for w in words if w[0].isalpha())
    if max_len > 0 and len(letters) > max_len: letters = letters[:max_len]
    return letters
