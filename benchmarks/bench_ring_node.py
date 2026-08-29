"""benchmarks/bench_ring_node.py — bench ring node."""
import argparse, json
def bench(n):
    from noesis_harness.ring_node import RingNode
    rn = RingNode(64)
    for i in range(n): rn.node(f"k{i}", i)
    return {"ops": n, "size": len(rn), "passed": len(rn) == min(n, 64)}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
