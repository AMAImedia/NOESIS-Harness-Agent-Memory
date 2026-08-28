"""benchmarks/bench_stats.py — benchmark stats.

Stdlib only, writes only to TEMP.
"""
from __future__ import annotations
import argparse, json, time

def bench(n: int):
    from noesis_harness.stats import mean, stdev
    xs = list(range(n))
    start = time.perf_counter()
    m = mean(xs); s = stdev(xs)
    sec = time.perf_counter() - start
    return {"ops": n, "mean": m, "stdev": s, "seconds": sec, "passed": m == (n - 1) / 2}

def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
