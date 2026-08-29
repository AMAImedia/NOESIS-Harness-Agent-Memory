"""benchmarks/bench_validate_util.py — bench validate util."""
import argparse, json
def bench(n):
    from noesis_harness.validate_util import required, in_range, validate_all
    checks = [lambda v: required(v), lambda v: in_range(v, 0, 100)]
    for i in range(n): validate_all(i % 100, checks)
    return {"ops": n, "passed": True}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0
if __name__ == "__main__": raise SystemExit(main())
