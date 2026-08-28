"""benchmarks/bench_histogram.py — benchmark Histogram.

Stdlib only, writes only to TEMP.
"""
from __future__ import annotations
import argparse, json, time

def bench(n: int):
    from noesis_harness.histogram import Histogram
    h = Histogram([10, 50, 100])
    start = time.perf_counter()
    for i in range(n): h.observe(i % 120)
    sec = time.perf_counter() - start
    return {"ops": n, "total": h.total, "seconds": sec, "passed": h.total == n}

def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
