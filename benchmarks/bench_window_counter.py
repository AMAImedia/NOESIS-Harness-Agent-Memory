"""benchmarks/bench_window_counter.py — bench window counter."""
import argparse, json
def bench(n):
    from noesis_harness.window_counter import WindowCounter
    w = WindowCounter(64)
    for i in range(n): w.add(float(i % 128))
    return {"ops": n, "avg": w.avg(), "passed": w.count() == min(n, 64)}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
