"""benchmarks/bench_queue_computed.py — bench queue computed."""
import argparse, json
def bench(n):
    from noesis_harness.queue_computed import QueueComputed
    qc = QueueComputed(0, lambda k: k)
    for i in range(n): qc.get(f"k{i}")
    return {"ops": n, "size": len(qc), "passed": len(qc) == n}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
