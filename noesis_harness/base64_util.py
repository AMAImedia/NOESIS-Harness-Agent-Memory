"""noesis_harness/base64_util.py — base64 helpers.

Patterns: LoopX base64.
Stdlib only.
"""
from __future__ import annotations
import base64

def encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")
def decode(text: str) -> bytes:
    return base64.b64decode(text)
def encode_str(text: str) -> str:
    return encode(text.encode("utf-8"))
def decode_str(text: str) -> str:
    return decode(text).decode("utf-8")
