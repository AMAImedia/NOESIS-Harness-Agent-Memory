"""benchmarks/bench_xml.py — bench XML parse."""
import argparse, json, time
def bench(n):
    from noesis_harness.xml_utils import from_string
    xml = "<root><a>hello</a><b>world</b></root>"
    s = time.perf_counter(); [from_string(xml) for _ in range(n)]; sec = time.perf_counter() - s
    return {"ops": n, "seconds": sec, "passed": True}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0
if __name__ == "__main__": raise SystemExit(main())
