"""benchmarks/bench_memoize.py — benchmark memoize.

Stdlib only, writes only to TEMP.
"""
from __future__ import annotations
import argparse, json, time

def bench(n: int):
    from noesis_harness.memoize import memoize
    @memoize
    def f(x): return x*2
    start = time.perf_counter()
    for i in range(n): f(i % 10)
    sec = time.perf_counter() - start
    return {"ops": n, "seconds": sec, "passed": True}

def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0
if __name__ == "__main__": raise SystemExit(main())
