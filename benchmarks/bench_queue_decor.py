"""benchmarks/bench_queue_decor.py — bench queue decor."""
import argparse, json
def bench(n):
    from noesis_harness.queue_decor import QueueDecor
    m = QueueDecor(0)
    @m.decor
    def f(x): return x
    for i in range(n): f(i)
    return {"ops": n, "size": len(m), "passed": len(m) == n}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
