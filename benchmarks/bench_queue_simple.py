"""benchmarks/bench_queue_simple.py — bench queue simple."""
import argparse, json
def bench(n):
    from noesis_harness.queue_simple import QueueSimple
    qs = QueueSimple(0)
    for i in range(n): qs.remember(f"k{i}", i)
    return {"ops": n, "size": len(qs), "passed": len(qs) == n}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
