"""benchmarks/bench_pubsub.py — benchmark PubSub.

Stdlib only, writes only to TEMP.
"""
from __future__ import annotations
import argparse, json, time

def bench(n: int):
    from noesis_harness.pubsub import PubSub
    ps = PubSub()
    got = []
    for _ in range(3): ps.subscribe("t", lambda m: got.append(m))
    start = time.perf_counter()
    for i in range(n): ps.publish("t", i)
    sec = time.perf_counter() - start
    return {"ops": n, "delivered": len(got), "seconds": sec, "passed": len(got) == n * 3}

def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
