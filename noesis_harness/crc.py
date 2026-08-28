"""noesis_harness/crc.py — CRC32 wrapper with hex helper.

Patterns: LoopX crc.
Stdlib only.
"""
from __future__ import annotations
import binascii
from typing import Any

def crc32(data: bytes) -> int:
    return binascii.crc32(data) & 0xFFFFFFFF
def crc_hex(data: bytes) -> str:
    return format(crc32(data), "08x")
def crc_str(text: str) -> str:
    return crc_hex(text.encode("utf-8"))
