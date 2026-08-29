"""benchmarks/bench_queue_stop.py — bench queue stop."""
import argparse, json
def bench(n):
    from noesis_harness.queue_stop import QueueStop
    qs = QueueStop(0)
    for i in range(n): qs.stop(f"k{i}", i)
    return {"ops": n, "size": len(qs), "passed": len(qs) == n}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
