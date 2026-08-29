"""benchmarks/bench_ring_priority.py — bench ring priority queue."""
import argparse, json
def bench(n):
    from noesis_harness.ring_priority import RingPriority
    q = RingPriority(64)
    for i in range(n): q.push(i % 128, i % 128)
    return {"ops": n, "size": len(q), "passed": len(q) == min(n, 64)}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
