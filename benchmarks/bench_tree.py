"""benchmarks/bench_tree.py — benchmark TreeNode.

Stdlib only, writes only to TEMP.
"""
from __future__ import annotations
import argparse, json, time

def bench(n: int):
    from noesis_harness.tree import TreeNode
    root = TreeNode(0)
    start = time.perf_counter()
    for i in range(1, n + 1): root.add(TreeNode(i))
    sec = time.perf_counter() - start
    return {"ops": n, "size": root.size(), "seconds": sec, "passed": root.size() == n + 1}

def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
