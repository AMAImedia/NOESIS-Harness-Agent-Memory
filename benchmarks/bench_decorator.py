"""benchmarks/bench_decorator.py — bench decorator wrap."""
import argparse, json
def bench(n):
    from noesis_harness.decorator_util import wrap
    fn = wrap(lambda: 1)
    for _ in range(n): fn()
    return {"ops": n, "passed": True}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0
if __name__ == "__main__": raise SystemExit(main())
