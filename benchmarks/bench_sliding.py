"""benchmarks/bench_sliding.py — benchmark SlidingWindow.

Stdlib only, writes only to TEMP.
"""
from __future__ import annotations
import argparse, json, time

def bench(n: int):
    from noesis_harness.sliding_window import SlidingWindow
    w = SlidingWindow(100)
    start = time.perf_counter()
    for i in range(n): w.add(i)
    sec = time.perf_counter() - start
    return {"items": n, "size": len(w), "seconds": sec, "passed": len(w) == min(n, 100)}

def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--items", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.items); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
