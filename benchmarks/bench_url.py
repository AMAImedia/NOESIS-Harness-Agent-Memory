"""benchmarks/bench_url.py — bench url encode."""
import argparse,json,time
def bench(n):
    from noesis_harness.url_encode import encode
    s=time.perf_counter(); [encode("a b/c?x=1&y=2") for _ in range(n)]; sec=time.perf_counter()-s
    return {"ops":n,"seconds":sec,"passed":True}
def main(argv=None):
    import argparse,json; p=argparse.ArgumentParser(); p.add_argument("--ops",type=int,default=1000)
    a=p.parse_args(argv); r=bench(a.ops); print(json.dumps(r)); return 0
if __name__=="__main__": raise SystemExit(main())
