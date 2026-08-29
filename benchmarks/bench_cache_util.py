"""benchmarks/bench_cache_util.py — bench cache util."""
import argparse, json
def bench(n):
    from noesis_harness.cache_util import CacheUtil
    c = CacheUtil(64)
    for i in range(n): c.put(f"k{i % 128}", i)
    return {"ops": n, "size": len(c), "passed": len(c) <= 64}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
