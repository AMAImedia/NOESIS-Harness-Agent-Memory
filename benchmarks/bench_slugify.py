"""benchmarks/bench_slugify.py — benchmark slugify.

Stdlib only, writes only to TEMP.
"""
from __future__ import annotations
import argparse, json, time

def bench(n: int):
    from noesis_harness.slugify import slugify
    text = "The Quick Brown Fox Jumps Over The Lazy Dog! "
    start = time.perf_counter()
    out = [slugify(text) for _ in range(n)]
    sec = time.perf_counter() - start
    return {"ops": n, "slug": out[0], "seconds": sec, "passed": out[0] == "the-quick-brown-fox-jumps-over-the-lazy-dog"}

def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
