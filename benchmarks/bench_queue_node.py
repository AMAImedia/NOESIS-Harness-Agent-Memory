"""benchmarks/bench_queue_node.py — bench queue node."""
import argparse, json
def bench(n):
    from noesis_harness.queue_node import QueueNode
    qn = QueueNode(0)
    for i in range(n): qn.node(f"k{i}", i)
    return {"ops": n, "size": len(qn), "passed": len(qn) == n}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
