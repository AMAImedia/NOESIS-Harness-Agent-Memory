"""noesis_harness/url_encode.py — percent encode/decode.

Patterns: LoopX codec.
Stdlib only.
"""
from __future__ import annotations
import urllib.parse

def encode(s: str) -> str: return urllib.parse.quote(s, safe="")
def decode(s: str) -> str: return urllib.parse.unquote(s)
def encode_plus(s: str) -> str: return urllib.parse.quote_plus(s)
