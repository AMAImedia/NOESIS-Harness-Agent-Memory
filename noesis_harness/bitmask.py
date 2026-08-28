"""noesis_harness/bitmask.py — bit flag helpers.

Patterns: LoopX bitmask.
Stdlib only.
"""
from __future__ import annotations

def set_bit(mask: int, bit: int) -> int:
    return mask | (1 << bit)
def clear_bit(mask: int, bit: int) -> int:
    return mask & ~(1 << bit)
def has_bit(mask: int, bit: int) -> bool:
    return bool(mask & (1 << bit))
def toggle_bit(mask: int, bit: int) -> int:
    return mask ^ (1 << bit)
