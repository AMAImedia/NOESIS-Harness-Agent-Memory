import unittest
import benchmarks.bench_memoize_ttl as bm

class TestBenchMemoizeTTL(unittest.TestCase):
    def test_main_zero(self): self.assertEqual(bm.main(["--ops","10"]),0)
    def test_passed(self): self.assertTrue(bm.bench(20)["passed"])
    def test_no_repo_writes(self):
        import os; repo=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        before=set()
        for r,ds,fs in os.walk(repo):
            if ".git" in ds: ds.remove(".git")
            if "_temp" in r or "dist" in r or "_archive" in r: continue
            for f in fs: before.add(os.path.join(r,f))
        bm.bench(10)
        after=set()
        for r,ds,fs in os.walk(repo):
            if ".git" in ds: ds.remove(".git")
            if "_temp" in r or "dist" in r or "_archive" in r: continue
            for f in fs: after.add(os.path.join(r,f))
        self.assertEqual(before,after)
    def test_determinism(self): self.assertEqual(bm.bench(10)["passed"], bm.bench(10)["passed"])
    def test_small(self): self.assertTrue(bm.bench(5)["passed"])
    def test_ops(self): self.assertEqual(bm.bench(7)["ops"],7)
    def test_lazy(self): import benchmarks.bench_memoize_ttl; self.assertTrue(hasattr(benchmarks.bench_memoize_ttl,"bench"))
