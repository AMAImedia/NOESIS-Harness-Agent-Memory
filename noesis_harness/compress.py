"""noesis_harness/compress.py — simple deterministic compression helpers.

Patterns: LoopX canonical payload (RLE-ish for repeated bytes).
Stdlib only.
"""
from __future__ import annotations
import zlib

def compress(data: bytes) -> bytes:
    return zlib.compress(data)

def decompress(data: bytes) -> bytes:
    return zlib.decompress(data)

def ratio(original: bytes) -> float:
    if not original: return 0.0
    return len(compress(original)) / len(original)
