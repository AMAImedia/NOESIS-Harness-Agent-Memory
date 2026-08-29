"""benchmarks/bench_queue_proxy.py — bench queue proxy."""
import argparse, json
def bench(n):
    from noesis_harness.queue_proxy import QueueProxy
    qp = QueueProxy(0)
    for i in range(n): qp.set(f"k{i}", i)
    return {"ops": n, "size": len(qp), "passed": len(qp) == n}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
