"""Run the 20-fact public recall bench. Stdlib only."""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from noesis_harness import Memory


def run(path=None):
    here = os.path.dirname(os.path.abspath(__file__))
    path = path or os.path.join(here, "recall20.json")
    with open(path, "r", encoding="utf-8") as fh:
        spec = json.load(fh)
    tmp = tempfile.mkdtemp(prefix="noesis_r20_")
    mem = Memory(os.path.join(tmp, "m.db"))
    for fact in spec["facts"]:
        mem.save(fact)
    hit = 0
    rows = []
    for item in spec["queries"]:
        got = mem.recall(item["q"], limit=3)
        blob = " ".join(h.get("fact", "") for h in got)
        ok = item["expect"].lower() in blob.lower()
        hit += int(ok)
        rows.append({"q": item["q"], "ok": ok})
    n = len(spec["queries"])
    return {"hit": hit, "n": n, "acc": hit / float(n) if n else 0.0, "rows": rows}


if __name__ == "__main__":
    out = run()
    print("recall20 %s/%s acc=%.2f" % (out["hit"], out["n"], out["acc"]))
    sys.exit(0 if out["acc"] >= 0.8 else 1)
