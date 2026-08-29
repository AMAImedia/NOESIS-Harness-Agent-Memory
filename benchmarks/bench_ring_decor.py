"""benchmarks/bench_ring_decor.py — bench ring decor."""
import argparse, json
def bench(n):
    from noesis_harness.ring_decor import RingDecor
    m = RingDecor(64)
    @m.decor
    def f(x): return x
    for i in range(n): f(i)
    return {"ops": n, "size": len(m), "passed": len(m) == min(n, 64)}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
