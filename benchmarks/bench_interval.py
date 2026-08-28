"""benchmarks/bench_interval.py — benchmark merge.

Stdlib only, writes only to TEMP.
"""
from __future__ import annotations
import argparse, json, time

def bench(n: int):
    from noesis_harness.interval import merge
    iv = [(i, i + 1) for i in range(0, 2 * n, 2)]
    start = time.perf_counter()
    res = merge(iv)
    sec = time.perf_counter() - start
    return {"ops": n, "ranges": len(res), "seconds": sec, "passed": len(res) == n}

def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
