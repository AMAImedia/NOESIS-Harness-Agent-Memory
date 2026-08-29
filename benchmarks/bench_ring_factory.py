"""benchmarks/bench_ring_factory.py — bench ring factory."""
import argparse, json
def bench(n):
    from noesis_harness.ring_factory import RingFactory
    rf = RingFactory(64, lambda k: k)
    for i in range(n): rf.get(f"k{i}")
    return {"ops": n, "size": len(rf), "passed": len(rf) == min(n, 64)}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
