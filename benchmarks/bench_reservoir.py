"""benchmarks/bench_reservoir.py — benchmark reservoir sampling.

Stdlib only, writes only to TEMP.
"""
from __future__ import annotations
import argparse, json, time

def bench(n: int):
    from noesis_harness.reservoir import sample
    stream = list(range(n))
    start = time.perf_counter()
    out = sample(stream, 10, seed=1)
    sec = time.perf_counter() - start
    return {"ops": n, "kept": len(out), "seconds": sec, "passed": len(out) == min(n, 10)}

def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
