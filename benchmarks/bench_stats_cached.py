"""benchmarks/bench_stats_cached.py — bench running stats."""
import argparse, json
def bench(n):
    from noesis_harness.stats_cached import RunningStats
    rs = RunningStats()
    for i in range(n): rs.update(float(i))
    return {"ops": n, "mean": rs.mean(), "passed": rs.count() == n}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
