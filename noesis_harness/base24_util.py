"""noesis_harness/base24_util.py — base24 encode/decode (human-friendly).

Patterns: LoopX codec.
Stdlib only.
"""
from __future__ import annotations

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

def encode(n: int) -> str:
    if n < 0: raise ValueError("n >=0")
    if n == 0: return _ALPHABET[0]
    out = []
    while n: out.append(_ALPHABET[n % 24]); n //= 24
    return "".join(reversed(out))

def decode(text: str) -> int:
    n = 0
    for ch in text.upper():
        idx = _ALPHABET.index(ch); n = n * 24 + idx
    return n
