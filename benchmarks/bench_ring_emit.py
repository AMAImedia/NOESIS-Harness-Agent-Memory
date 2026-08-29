"""benchmarks/bench_ring_emit.py — bench ring emit."""
import argparse, json
def bench(n):
    from noesis_harness.ring_emit import RingEmit
    re = RingEmit(64)
    for i in range(n): re.emit(f"k{i}", i)
    return {"ops": n, "size": len(re), "passed": len(re) == min(n, 64)}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
