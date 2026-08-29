"""benchmarks/bench_ring_hold.py — bench ring hold."""
import argparse, json
def bench(n):
    from noesis_harness.ring_hold import RingHold
    rh = RingHold(64)
    for i in range(n): rh.hold(f"k{i}", i)
    return {"ops": n, "size": len(rh), "passed": len(rh) == min(n, 64)}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
