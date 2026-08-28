"""benchmarks/bench_event_stream.py — benchmark event_stream.

Stdlib only, writes only to TEMP.
"""
from __future__ import annotations
import argparse, json, os, sys, tempfile, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

def bench(n: int):
    from noesis_harness.event_store import EventStore
    import noesis_harness.event_stream as es
    scratch = tempfile.mkdtemp(prefix="noesis_bench_es_")
    path = os.path.join(scratch, "e.jsonl")
    s = EventStore(path)
    for i in range(n): s.append("note", {"i": i}, event_id=f"e{i}")
    start = time.perf_counter()
    total = sum(len(b) for b in es.stream(path, 100))
    sec = time.perf_counter() - start
    return {"events": n, "total": total, "seconds": sec, "passed": total == n}

def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--events", type=int, default=500)
    a = p.parse_args(argv); r = bench(a.events); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
