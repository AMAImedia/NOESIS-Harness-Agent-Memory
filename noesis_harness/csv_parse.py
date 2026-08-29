"""noesis_harness/csv_parse.py — minimal CSV parse/unparse.

Patterns: LoopX csv.
Stdlib only.
"""
from __future__ import annotations
import csv, io

def parse(text: str) -> list:
    return list(csv.reader(io.StringIO(text)))
def unparse(rows: list) -> str:
    out=io.StringIO(); w=csv.writer(out, lineterminator="\n"); w.writerows(rows); return out.getvalue()
