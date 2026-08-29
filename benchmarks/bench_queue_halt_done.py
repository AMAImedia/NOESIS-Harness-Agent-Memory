"""benchmarks/bench_queue_halt_done.py — bench queue halt_done."""
import argparse, json
def bench(n):
    from noesis_harness.queue_halt_done import QueueHaltDone
    qh = QueueHaltDone(0)
    for i in range(n): qh.halt_done(f"k{i}", i)
    return {"ops": n, "size": len(qh), "passed": len(qh) == n}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
