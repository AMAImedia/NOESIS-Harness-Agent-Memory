"""benchmarks/bench_memoize_ttl.py — bench memoize TTL."""
import argparse, json
def bench(n):
    from noesis_harness.memoize_ttl import MemoTTL
    m = MemoTTL(60)
    for i in range(n): m.put(f"k{i}", i)
    return {"ops": n, "passed": len(m) == n}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
