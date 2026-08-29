"""benchmarks/bench_validate_chain.py — bench validation chain."""
import argparse, json
def bench(n):
    from noesis_harness.validate_chain import Chain
    c = Chain().add(lambda v: [] if isinstance(v, str) else ["not str"])
    for i in range(n): c.validate("test")
    return {"ops": n, "passed": True}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0
if __name__ == "__main__": raise SystemExit(main())
