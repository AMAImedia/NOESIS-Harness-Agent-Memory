"""benchmarks/bench_retry_util.py — bench retry."""
import argparse, json
def bench(n):
    from noesis_harness.retry_util import retry
    for _ in range(n): retry(lambda: 1, max_attempts=1, delay=0)
    return {"ops": n, "passed": True}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0
if __name__ == "__main__": raise SystemExit(main())
