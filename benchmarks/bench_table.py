"""benchmarks/bench_table.py — benchmark format_table.

Stdlib only, writes only to TEMP.
"""
from __future__ import annotations
import argparse, json, time

def bench(n: int):
    from noesis_harness.table import format_table
    rows = [[str(i), str(i * 2)] for i in range(n)]
    start = time.perf_counter()
    out = format_table(["x", "y"], rows)
    sec = time.perf_counter() - start
    return {"ops": n, "lines": out.count("\n") + 1, "seconds": sec, "passed": out.count("\n") + 1 == n + 2}

def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
