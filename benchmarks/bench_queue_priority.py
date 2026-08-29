"""benchmarks/bench_queue_priority.py — bench priority queue."""
import argparse, json
def bench(n):
    from noesis_harness.queue_priority import PriorityQueue
    q = PriorityQueue()
    for i in range(n): q.push(i, i)
    popped = 0
    while q.pop() is not None: popped += 1
    return {"ops": n, "popped": popped, "passed": popped == n}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
