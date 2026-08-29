"""benchmarks/bench_retry_async.py — bench retry sync."""
import argparse, json
def bench(n):
    from noesis_harness.retry_async import retry_sync
    for _ in range(n): retry_sync(lambda: 1, max_attempts=1, delay=0)
    return {"ops": n, "passed": True}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0
if __name__ == "__main__": raise SystemExit(main())
