"""benchmarks/bench_queue_map.py — bench queue map."""
import argparse, json
def bench(n):
    from noesis_harness.queue_map import QueueMap
    qm = QueueMap(0)
    for i in range(n): qm.mapping(f"k{i}", i)
    return {"ops": n, "size": len(qm), "passed": len(qm) == n}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
