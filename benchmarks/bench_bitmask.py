"""benchmarks/bench_bitmask.py — benchmark bitmask.

Stdlib only, writes only to TEMP.
"""
from __future__ import annotations
import argparse, json, time

def bench(n: int):
    from noesis_harness.bitmask import set_bit, has_bit
    m = 0
    start = time.perf_counter()
    for i in range(n): m = set_bit(m, i % 8)
    sec = time.perf_counter() - start
    return {"ops": n, "passed": has_bit(m, 0)}

def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
