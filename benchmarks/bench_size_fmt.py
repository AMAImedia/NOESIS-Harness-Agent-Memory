"""benchmarks/bench_size_fmt.py — benchmark format_bytes.

Stdlib only, writes only to TEMP.
"""
from __future__ import annotations
import argparse, json, time

def bench(n: int):
    from noesis_harness.size_fmt import format_bytes
    sizes = [0, 512, 1024, 1024 * 1024, 1024 * 1024 * 1024]
    start = time.perf_counter()
    out = [format_bytes(sizes[i % len(sizes)]) for i in range(n)]
    sec = time.perf_counter() - start
    return {"ops": n, "sample": out[1], "seconds": sec, "passed": out[1] == "512 B"}

def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
