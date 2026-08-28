"""noesis_harness/enum_util.py — string enum helpers.

Patterns: LoopX enum utilities.
Stdlib only.
"""
from __future__ import annotations
from typing import List

def values(mapping: dict) -> List[str]:
    return list(mapping.values())
def is_valid(mapping: dict, value: str) -> bool:
    return value in set(mapping.values())
def names(mapping: dict) -> List[str]:
    return list(mapping.keys())
