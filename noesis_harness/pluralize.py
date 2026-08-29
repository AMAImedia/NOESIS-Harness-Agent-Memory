"""noesis_harness/pluralize.py — simple English pluralize.

Patterns: LoopX plural.
Stdlib only.
"""
from __future__ import annotations

def plural(n: int, singular: str, plural_form: str = None) -> str:
    if n==1: return singular
    if plural_form: return plural_form
    if singular.endswith("y") and singular[-2:-1] not in "aeiou": return singular[:-1]+"ies"
    if singular.endswith(("s","x","z","ch","sh")): return singular+"es"
    return singular+"s"
