"""benchmarks/bench_lru.py — benchmark LRUCache.

Stdlib only, writes only to TEMP.
"""
from __future__ import annotations
import argparse, json, time

def bench(n: int):
    from noesis_harness.lru_cache import LRUCache
    c = LRUCache(64)
    start = time.perf_counter()
    for i in range(n): c.put(i % 128, i)
    sec = time.perf_counter() - start
    return {"ops": n, "size": len(c), "seconds": sec, "passed": len(c) == min(n, 64)}

def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
