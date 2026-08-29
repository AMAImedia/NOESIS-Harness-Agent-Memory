"""noesis_harness/template.py — {{var}} substitution.

Patterns: LoopX template.
Stdlib only.
"""
from __future__ import annotations
import re

_pat=re.compile(r"\{\{\s*(\w+)\s*\}\}")

def render(text: str, ctx: dict) -> str:
    def repl(m): return str(ctx.get(m.group(1), m.group(0)))
    return _pat.sub(repl, text)
