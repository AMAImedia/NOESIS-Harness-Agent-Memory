"""benchmarks/bench_invariant.py — benchmark invariant checker.

Patterns: LoopX read-only invariant evaluation.
Stdlib only, writes only to TEMP.
"""
from __future__ import annotations
import argparse, json, os, sys, tempfile, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

def bench(events: int):
    from noesis_harness.event_store import EventStore
    import noesis_harness.invariant as inv
    scratch = tempfile.mkdtemp(prefix="noesis_bench_inv_")
    path = os.path.join(scratch, "e.jsonl")
    s = EventStore(path)
    for i in range(events): s.append("note", {"n": i, "text": "x"*20}, event_id=f"e{i}")
    rules = [{"name": "has_n", "fn": lambda store: None if all("n" in r.get("payload", {}) for r in store.iter_events()) else "missing n"}]
    start = time.perf_counter()
    res = inv.check(path, rules)
    sec = time.perf_counter() - start
    return {"events": events, "seconds": sec, "passed": res["passed"]}

def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--events", type=int, default=500)
    a = p.parse_args(argv); r = bench(a.events); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
