"""benchmarks/bench_ring_exit.py — bench ring exit."""
import argparse, json
def bench(n):
    from noesis_harness.ring_exit import RingExit
    re = RingExit(64)
    for i in range(n): re.exit(f"k{i}", i)
    return {"ops": n, "size": len(re), "passed": len(re) == min(n, 64)}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
