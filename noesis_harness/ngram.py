"""noesis_harness/ngram.py — character n-grams.

Patterns: LoopX ngram.
Stdlib only.
"""
from __future__ import annotations
from typing import List

def char_ngrams(text: str, n: int) -> List[str]:
    if n < 1: raise ValueError("n >=1")
    if len(text) < n: return []
    return [text[i:i + n] for i in range(len(text) - n + 1)]
