"""benchmarks/bench_counter.py — benchmark Counter.

Stdlib only, writes only to TEMP.
"""
from __future__ import annotations
import argparse, json, time

def bench(n: int):
    from noesis_harness.counter import Counter
    c = Counter()
    start = time.perf_counter()
    for _ in range(n): c.inc()
    sec = time.perf_counter() - start
    return {"ops": n, "count": c.get(), "seconds": sec, "passed": c.get() == n}

def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=10000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
