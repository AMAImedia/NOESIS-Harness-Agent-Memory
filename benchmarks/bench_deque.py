"""benchmarks/bench_deque.py — benchmark BoundedDeque.

Stdlib only, writes only to TEMP.
"""
from __future__ import annotations
import argparse, json, time

def bench(n: int):
    from noesis_harness.deque import BoundedDeque
    d = BoundedDeque(100)
    start = time.perf_counter()
    for i in range(n): d.append(i)
    sec = time.perf_counter() - start
    return {"ops": n, "size": len(d), "seconds": sec, "passed": len(d) == min(n, 100)}

def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
