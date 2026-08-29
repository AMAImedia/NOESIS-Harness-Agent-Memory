"""noesis_harness/string_util.py — string helpers.

Patterns: LoopX string util.
Stdlib only.
"""
from __future__ import annotations

def is_empty(s: str) -> bool:
    return not s or s.strip() == ""
def reverse(s: str) -> str:
    return s[::-1]
def count_char(s: str, c: str) -> int:
    return s.count(c)
def is_palindrome(s: str) -> bool:
    clean = "".join(ch.lower() for ch in s if ch.isalnum())
    return clean == clean[::-1]
def title_case(s: str) -> str:
    return s.title()
