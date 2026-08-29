"""benchmarks/bench_crypto.py — bench HMAC sign."""
import argparse, json, time
def bench(n):
    from noesis_harness.crypto_hmac import sign
    s = time.perf_counter(); [sign(b"key", b"data") for _ in range(n)]; sec = time.perf_counter() - s
    return {"ops": n, "seconds": sec, "passed": True}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0
if __name__ == "__main__": raise SystemExit(main())
