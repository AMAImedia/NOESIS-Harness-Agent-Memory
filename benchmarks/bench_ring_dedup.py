"""benchmarks/bench_ring_dedup.py — bench ring dedup."""
import argparse, json
def bench(n):
    from noesis_harness.ring_dedup import RingDedup
    r = RingDedup(64)
    for i in range(n): r.add(i % 128)
    return {"ops": n, "size": len(r), "passed": len(r) <= 64}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
