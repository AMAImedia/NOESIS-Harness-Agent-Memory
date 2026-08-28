"""noesis_harness/args.py — minimal argv parser.

Patterns: LoopX args.
Stdlib only.
"""
from __future__ import annotations
from typing import Dict, List

def parse(argv: List[str]) -> Dict[str, object]:
    out: Dict[str, object] = {"_": []}
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok.startswith("--"):
            key = tok[2:]
            if "=" in key:
                k, v = key.split("=", 1); out[k] = v
            elif i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                out[key] = argv[i + 1]; i += 1
            else:
                out[key] = True
        elif tok.startswith("-") and len(tok) > 1:
            out[tok[1:]] = True
        else:
            out["_"].append(tok)
        i += 1
    return out
