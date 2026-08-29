"""benchmarks/bench_queue_factory.py — bench queue factory."""
import argparse, json
def bench(n):
    from noesis_harness.queue_factory import QueueFactory
    qf = QueueFactory(0, lambda k: k)
    for i in range(n): qf.get(f"k{i}")
    return {"ops": n, "size": len(qf), "passed": len(qf) == n}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
