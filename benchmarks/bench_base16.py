"""benchmarks/bench_base16.py — bench base16 encode."""
import argparse, json
def bench(n):
    from noesis_harness.base16_util import encode
    for _ in range(n): encode(b"hello world data")
    return {"ops": n, "passed": True}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0
if __name__ == "__main__": raise SystemExit(main())
