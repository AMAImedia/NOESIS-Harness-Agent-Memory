"""benchmarks/bench_queue_hold.py — bench queue hold."""
import argparse, json
def bench(n):
    from noesis_harness.queue_hold import QueueHold
    qh = QueueHold(0)
    for i in range(n): qh.hold(f"k{i}", i)
    return {"ops": n, "size": len(qh), "passed": len(qh) == n}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
