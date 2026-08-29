"""benchmarks/bench_chunked_write.py — bench chunked write."""
import argparse, json, os, tempfile
def bench(n):
    from noesis_harness.chunked_write import write_chunks
    tmp = tempfile.mkdtemp(); p = os.path.join(tmp, "bench.bin")
    chunks = [b"x" * 100 for _ in range(n)]
    write_chunks(p, iter(chunks))
    return {"ops": n, "passed": os.path.getsize(p) == n * 100}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
