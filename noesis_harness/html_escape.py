"""noesis_harness/html_escape.py — HTML escape/unescape.

Patterns: LoopX escape.
Stdlib only.
"""
from __future__ import annotations
import html

def escape(s: str) -> str: return html.escape(s, quote=True)
def unescape(s: str) -> str: return html.unescape(s)
