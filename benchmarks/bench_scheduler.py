"""benchmarks/bench_scheduler.py — benchmark Scheduler.

Stdlib only, writes only to TEMP.
"""
from __future__ import annotations
import argparse, json, time

def bench(n: int):
    from noesis_harness.scheduler import Scheduler
    s = Scheduler()
    calls = []
    for _ in range(5): s.every(1.0, lambda: calls.append(1))
    start = time.perf_counter()
    for _ in range(n): s.run_pending(1.0)
    sec = time.perf_counter() - start
    return {"ops": n, "calls": len(calls), "seconds": sec, "passed": len(calls) == n * 5}

def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
