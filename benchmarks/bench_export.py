"""benchmarks/bench_export.py — benchmark export_jsonl.

Stdlib only, writes only to TEMP.
"""
from __future__ import annotations
import argparse, json, os, sys, tempfile, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

def bench(events: int):
    from noesis_harness.event_store import EventStore
    import noesis_harness.export_jsonl as ex
    scratch = tempfile.mkdtemp(prefix="noesis_bench_exp_")
    src = os.path.join(scratch, "src.jsonl"); dst = os.path.join(scratch, "dst.jsonl")
    s = EventStore(src)
    for i in range(events): s.append("note", {"n": i}, event_id=f"e{i}")
    start = time.perf_counter()
    cnt = ex.export(src, dst)
    sec = time.perf_counter() - start
    return {"events": events, "count": cnt, "seconds": sec, "passed": cnt == events}

def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--events", type=int, default=500)
    a = p.parse_args(argv); r = bench(a.events); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
