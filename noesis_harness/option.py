"""noesis_harness/option.py — Option Some/None.

Patterns: LoopX option.
Stdlib only.
"""
from __future__ import annotations
from typing import Any

class Some:
    def __init__(self, value: Any): self.value = value
    def is_some(self): return True
    def is_none(self): return False
    def unwrap(self): return self.value
    def unwrap_or(self, default): return self.value

class Nothing:
    def is_some(self): return False
    def is_none(self): return True
    def unwrap(self): raise ValueError("None")
    def unwrap_or(self, default): return default

NONE = Nothing()
def some(v): return Some(v)
def none(): return NONE
