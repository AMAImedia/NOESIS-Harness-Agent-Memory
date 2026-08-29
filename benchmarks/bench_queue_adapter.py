"""benchmarks/bench_queue_adapter.py — bench queue adapter."""
import argparse, json
def bench(n):
    from noesis_harness.queue_adapter import QueueAdapter
    qa = QueueAdapter(0)
    for i in range(n): qa.adapt(f"k{i}", i)
    return {"ops": n, "size": len(qa), "passed": len(qa) == n}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
