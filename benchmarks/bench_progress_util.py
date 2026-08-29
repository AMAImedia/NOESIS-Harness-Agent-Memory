"""benchmarks/bench_progress_util.py — bench progress tracker."""
import argparse, json
def bench(n):
    from noesis_harness.progress_util import ProgressTracker
    p = ProgressTracker(n); [p.tick() for _ in range(n)]
    return {"ops": n, "passed": p.finished()}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
