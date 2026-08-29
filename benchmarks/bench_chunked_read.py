"""benchmarks/bench_chunked_read.py — bench chunked read."""
import argparse, json
def bench(n):
    from noesis_harness.chunked_read import chunked
    list(chunked(range(n), 10))
    return {"ops": n, "passed": True}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0
if __name__ == "__main__": raise SystemExit(main())
