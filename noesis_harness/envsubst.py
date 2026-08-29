"""noesis_harness/envsubst.py — $VAR / ${VAR} substitution.

Patterns: LoopX envsubst.
Stdlib only.
"""
from __future__ import annotations
import re

_pat=re.compile(r"\$\{(\w+)\}|\$(\w+)")

def subst(text: str, env: dict) -> str:
    def repl(m): k=m.group(1) or m.group(2); return str(env.get(k, m.group(0)))
    return _pat.sub(repl, text)
