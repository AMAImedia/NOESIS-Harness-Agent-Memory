"""benchmarks/bench_atomic_write.py — benchmark atomic_write (TEMP only).

Stdlib only, writes only to TEMP.
"""
from __future__ import annotations
import argparse, json, os, tempfile, time

def bench(n: int):
    import noesis_harness.atomic_write as aw
    tmp = tempfile.mkdtemp(prefix="noesis_bench_aw_")
    path = os.path.join(tmp, "out.bin")
    start = time.perf_counter()
    for i in range(n): aw.atomic_write(path, str(i).encode(), tmp_dir=tmp)
    sec = time.perf_counter() - start
    return {"ops": n, "final": open(path, "rb").read().decode(), "seconds": sec, "passed": open(path, "rb").read() == str(n - 1).encode()}

def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
