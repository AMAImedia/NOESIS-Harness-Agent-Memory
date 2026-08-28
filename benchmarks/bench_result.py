"""benchmarks/bench_result.py — benchmark Result.

Stdlib only, writes only to TEMP.
"""
from __future__ import annotations
import argparse, json, time

def bench(n: int):
    from noesis_harness.result import ok, err
    start = time.perf_counter()
    for i in range(n):
        r = ok(i) if i % 2 == 0 else err(str(i))
        r.is_ok()
    sec = time.perf_counter() - start
    return {"ops": n, "seconds": sec, "passed": True}

def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0
if __name__ == "__main__": raise SystemExit(main())
