"""noesis_harness/slugify.py — slugify text.

Patterns: LoopX slugify.
Stdlib only.
"""
from __future__ import annotations
import re, unicodedata

def slugify(text: str, max_len: int = 64) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    text = re.sub(r"-+", "-", text)
    if max_len > 0 and len(text) > max_len: text = text[:max_len].rstrip("-")
    return text
