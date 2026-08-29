"""benchmarks/bench_queue_wait.py — bench queue wait."""
import argparse, json
def bench(n):
    from noesis_harness.queue_wait import QueueWait
    qw = QueueWait(0)
    for i in range(n): qw.wait(f"k{i}", i)
    return {"ops": n, "size": len(qw), "passed": len(qw) == n}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
