"""benchmarks/bench_topo.py — benchmark topo sort.

Stdlib only.
"""
import argparse, json, time
def bench(n):
    from noesis_harness.topo_sort import topo_sort
    nodes=[str(i) for i in range(n)]; edges=[(str(i),str(i+1)) for i in range(n-1)]
    s=time.perf_counter(); r=topo_sort(nodes,edges); sec=time.perf_counter()-s
    return {"ops":n,"seconds":sec,"passed":len(r)==n}
def main(argv=None):
    import argparse, json
    p=argparse.ArgumentParser(); p.add_argument("--ops",type=int,default=1000)
    a=p.parse_args(argv); r=bench(a.ops); print(json.dumps(r)); return 0 if r["passed"] else 1
if __name__=="__main__": raise SystemExit(main())
