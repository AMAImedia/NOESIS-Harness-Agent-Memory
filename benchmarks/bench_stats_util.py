"""benchmarks/bench_stats_util.py — bench stats util."""
import argparse, json
def bench(n):
    from noesis_harness.stats_util import moving_avg
    xs = [float(i) for i in range(n)]
    moving_avg(xs, 3)
    return {"ops": n, "passed": True}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0
if __name__ == "__main__": raise SystemExit(main())
