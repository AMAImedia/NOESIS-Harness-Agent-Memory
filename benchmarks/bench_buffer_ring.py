"""benchmarks/bench_buffer_ring.py — bench byte buffer."""
import argparse, json
def bench(n):
    from noesis_harness.buffer_ring import ByteBuffer
    b = ByteBuffer(64)
    for i in range(n): b.write(bytes([i % 256]))
    return {"ops": n, "size": b.available(), "passed": b.available() == min(n, 64)}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
