"""noesis_harness/hex_util.py — hex helpers.

Patterns: LoopX hex.
Stdlib only.
"""
from __future__ import annotations

def to_hex(data: bytes) -> str:
    return data.hex()
def from_hex(text: str) -> bytes:
    return bytes.fromhex(text)
def to_hex_str(text: str) -> str:
    return to_hex(text.encode("utf-8"))
def from_hex_str(text: str) -> str:
    return from_hex(text).decode("utf-8")
