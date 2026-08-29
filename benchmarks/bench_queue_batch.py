"""benchmarks/bench_queue_batch.py — bench queue batch."""
import argparse, json
def bench(n):
    from noesis_harness.queue_batch import QueueBatch
    q = QueueBatch(n)
    q.push_batch(list(range(n)))
    taken = q.pop_batch(n)
    return {"ops": n, "taken": len(taken), "passed": len(taken) == n}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
