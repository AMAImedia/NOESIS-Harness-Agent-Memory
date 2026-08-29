"""noesis_harness/base32_util.py — base32 encode/decode.

Patterns: LoopX codec.
Stdlib only.
"""
from __future__ import annotations
import base64

def encode(data: bytes) -> str:
    return base64.b32encode(data).decode("ascii")
def decode(text: str) -> bytes:
    return base64.b32decode(text)
