"""benchmarks/bench_duration.py — benchmark duration parse.

Stdlib only, writes only to TEMP.
"""
from __future__ import annotations
import argparse, json, time

def bench(n: int):
    from noesis_harness.duration import parse
    start = time.perf_counter()
    total = 0.0
    for i in range(n): total += parse("1h30m")
    sec = time.perf_counter() - start
    return {"ops": n, "total": total, "seconds": sec, "passed": total == 5400.0 * n}

def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
