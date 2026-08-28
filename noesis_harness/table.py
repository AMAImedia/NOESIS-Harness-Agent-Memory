"""noesis_harness/table.py — ASCII table formatter.

Patterns: LoopX table.
Stdlib only.
"""
from __future__ import annotations
from typing import List

def format_table(headers: List[str], rows: List[List[str]]) -> str:
    cols = len(headers)
    widths = [len(str(h)) for h in headers]
    for row in rows:
        for i in range(min(len(row), cols)):
            widths[i] = max(widths[i], len(str(row[i])))
    def fmt(cells):
        return "| " + " | ".join(str(c).ljust(widths[i]) for i, c in enumerate(cells)) + " |"
    out = [fmt(headers)]
    out.append("+" + "+".join("-" * (w + 2) for w in widths) + "+")
    for row in rows:
        out.append(fmt(row))
    return "\n".join(out)
