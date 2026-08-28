"""benchmarks/bench_cron.py — benchmark cron matches.

Stdlib only, writes only to TEMP.
"""
from __future__ import annotations
import argparse, json, time

def bench(n: int):
    from noesis_harness.cron import matches
    start = time.perf_counter()
    ok = 0
    for i in range(n): ok += 1 if matches("*/5 * * * *", (i * 5) % 60, 0, 1, 1, 0) else 0
    sec = time.perf_counter() - start
    return {"ops": n, "matched": ok, "seconds": sec, "passed": ok == n}

def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
