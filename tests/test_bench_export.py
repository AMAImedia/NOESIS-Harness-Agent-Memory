import unittest
import benchmarks.bench_export as bm

class TestBenchExp(unittest.TestCase):
    def test_main_returns_zero(self): self.assertEqual(bm.main(["--events", "10"]), 0)
    def test_bench_passed(self): self.assertTrue(bm.bench(20)["passed"])
    def test_no_repo_writes(self):
        import os
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        before = set()
        for r, ds, fs in os.walk(repo):
            if ".git" in ds: ds.remove(".git")
            if "_temp" in r or "dist" in r or "_archive" in r: continue
            for f in fs: before.add(os.path.join(r, f))
        bm.bench(10)
        after = set()
        for r, ds, fs in os.walk(repo):
            if ".git" in ds: ds.remove(".git")
            if "_temp" in r or "dist" in r or "_archive" in r: continue
            for f in fs: after.add(os.path.join(r, f))
        self.assertEqual(before, after)
    def test_determinism(self): self.assertEqual(bm.bench(10)["passed"], bm.bench(10)["passed"])
    def test_lazy(self): import benchmarks.bench_export; self.assertTrue(hasattr(benchmarks.bench_export, "bench"))
    def test_small(self): self.assertTrue(bm.bench(5)["passed"])
    def test_count(self): self.assertEqual(bm.bench(7)["count"], 7)
