"""benchmarks/bench_base24.py — bench base24 encode."""
import argparse, json
def bench(n):
    from noesis_harness.base24_util import encode
    for i in range(n): encode(i % 1000)
    return {"ops": n, "passed": True}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0
if __name__ == "__main__": raise SystemExit(main())
