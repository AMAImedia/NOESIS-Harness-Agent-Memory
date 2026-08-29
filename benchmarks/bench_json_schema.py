"""benchmarks/bench_json_schema.py — bench JSON schema validation."""
import argparse, json, time
def bench(n):
    from noesis_harness.json_schema import validate
    schema = {"type": "object", "properties": {"name": {"type": "string"}, "age": {"type": "integer"}}, "required": ["name", "age"]}
    data = {"name": "Bob", "age": 30}
    s = time.perf_counter(); [validate(data, schema) for _ in range(n)]; sec = time.perf_counter() - s
    return {"ops": n, "seconds": sec, "passed": True}
def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--ops", type=int, default=1000)
    a = p.parse_args(argv); r = bench(a.ops); print(json.dumps(r)); return 0
if __name__ == "__main__": raise SystemExit(main())
