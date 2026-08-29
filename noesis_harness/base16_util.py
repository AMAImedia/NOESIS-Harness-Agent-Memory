"""noesis_harness/base16_util.py — base16 encode/decode.

Patterns: LoopX codec.
Stdlib only.
"""
from __future__ import annotations

def encode(data: bytes) -> str:
    return data.hex()
def decode(text: str) -> bytes:
    return bytes.fromhex(text)
