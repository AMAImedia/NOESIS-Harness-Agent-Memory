"""Text normalization utilities for the NOESIS harness agent memory.

Patterns borrowed from:
- LoopX: deterministic, side-effect-free token/string helpers used in replay
  projections and idempotent event fingerprinting.
- agentmemory: ASCII folding and whitespace normalization for stable memory
  keys and searchable content normalization.

This module is pure and deterministic: no LLM calls, no I/O, no state. Every
function maps a string to a string (or list of strings) such that repeated
calls with identical input produce identical output.
"""

import re
import unicodedata

_WS_RE = re.compile(r"\s+")


def normalize_ws(s):
    """Collapse all whitespace runs into single ASCII spaces and trim ends.

    Tabs, newlines, carriage returns, and multiple spaces all become one
    space. Leading and trailing whitespace is removed. The empty string and
    all-whitespace input yield the empty string.
    """
    if s is None:
        raise TypeError("normalize_ws requires a str, got None")
    return _WS_RE.sub(" ", s).strip()


def to_ascii_fold(s):
    """Normalize to NFKC then strip accents/markings to produce ASCII text.

    Applies Unicode NFKC normalization (compatibility decomposition, e.g.
    fullwidth -> ASCII, ligatures -> components) then removes combining
    marks so diacritics fold to their base letter. Non-ASCII base characters
    that cannot be folded are dropped.
    """
    if s is None:
        raise TypeError("to_ascii_fold requires a str, got None")
    normalized = unicodedata.normalize("NFKC", s)
    folded = []
    for ch in normalized:
        if ord(ch) < 128:
            folded.append(ch)
            continue
        decomp = unicodedata.normalize("NFD", ch)
        base = "".join(c for c in decomp if not unicodedata.combining(c))
        if base and ord(base[0]) < 128:
            folded.append(base[0])
    return "".join(folded)


def tokenize(s):
    """Lowercase and split into contiguous alphanumeric tokens.

    Input is ASCII-folded first so accented words normalize to ASCII before
    tokenization. Tokens are lowercase, contain only [a-z0-9], and punctuation
    or whitespace separates them. Returns an empty list for empty/blank input.
    """
    if s is None:
        raise TypeError("tokenize requires a str, got None")
    folded = to_ascii_fold(s).lower()
    return re.findall(r"[a-z0-9]+", folded)


def truncate(s, n):
    """Truncate to at most n characters, preserving the prefix.

    If n is None, negative, or the string is already within budget, the
    original string is returned unchanged. Never raises for valid inputs.
    """
    if s is None:
        raise TypeError("truncate requires a str, got None")
    if n is None or n < 0:
        return s
    if len(s) <= n:
        return s
    return s[:n]
