"""benchmarks/bench_union.py — benchmark DSU.

Stdlib only.
"""
import argparse, json, time
def bench(n):
    from noesis_harness.union_find import DSU
    d=DSU(); s=time.perf_counter()
    for i in range(n): d.union(str(i), str(i+1))
    for i in range(n): d.connected("0", str(i))
    sec=time.perf_counter()-s
    return {"ops":n,"seconds":sec,"passed": d.connected("0", str(n))}
def main(argv=None):
    import argparse, json
    p=argparse.ArgumentParser(); p.add_argument("--ops",type=int,default=1000)
    a=p.parse_args(argv); r=bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__=="__main__": raise SystemExit(main())
