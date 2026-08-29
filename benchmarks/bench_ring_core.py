"""benchmarks/bench_ring_core.py — bench ring core."""
import argparse, json
def bench(n):
    from noesis_harness.ring_core import RingCore
    rc = RingCore(64)
    for i in range(n): rc.core(f"k{i}", i)
    return {"ops": n, "size": len(rc), "passed": len(rc) == min(n, 64)}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
