"""benchmarks/bench_ttl_cache.py — benchmark TTLCache.

Stdlib only, writes only to TEMP.
"""
from __future__ import annotations
import argparse, json, time

def bench(n: int):
    from noesis_harness.ttl_cache import TTLCache
    c = TTLCache(ttl=1000)
    start = time.perf_counter()
    for i in range(n): c.put(f"k{i}", i, now=0)
    sec = time.perf_counter() - start
    return {"items": n, "size": len(c), "seconds": sec, "passed": len(c) == n}

def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--items", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.items); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
