"""benchmarks/bench_queue_parallel.py — bench queue parallel."""
import argparse, json
def bench(n):
    from noesis_harness.queue_parallel import QueueParallel
    q = QueueParallel()
    for i in range(n): q.push(i)
    popped = 0
    while q.pop() is not None: popped += 1
    return {"ops": n, "popped": popped, "passed": popped == n}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
