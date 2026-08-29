"""benchmarks/bench_chunked_jsonl.py — bench chunked jsonl."""
import argparse, json, os, tempfile
def bench(n):
    from noesis_harness.chunked_jsonl import write_jsonl, read_chunks
    tmp = tempfile.mkdtemp(); p = os.path.join(tmp, "bench.jsonl")
    items = [{"i": i} for i in range(n)]
    write_jsonl(p, items)
    total = sum(len(c) for c in read_chunks(p, 100))
    return {"ops": n, "total": total, "passed": total == n}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
