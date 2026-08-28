"""noesis_harness/tokenize.py — simple word tokenizer.

Patterns: LoopX tokenizer.
Stdlib only.
"""
from __future__ import annotations
import re

_WORD = re.compile(r"[A-Za-z0-9]+")

def tokens(text: str) -> list:
    return _WORD.findall(text)
def tokens_lower(text: str) -> list:
    return [t.lower() for t in _WORD.findall(text)]
def count_words(text: str) -> int:
    return len(_WORD.findall(text))
