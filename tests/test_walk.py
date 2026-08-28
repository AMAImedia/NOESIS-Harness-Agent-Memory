import os, tempfile, unittest
from noesis_harness.walk import walk

class TestWalk(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmp, "sub"))
        open(os.path.join(self.tmp, "a.py"), "w").write("x")
        open(os.path.join(self.tmp, "b.txt"), "w").write("x")
        open(os.path.join(self.tmp, "sub", "c.py"), "w").write("x")
    def test_all(self): files = walk(self.tmp); self.assertEqual(len(files), 3)
    def test_ext(self): files = walk(self.tmp, ".py"); self.assertEqual(len(files), 2)
    def test_sorted(self): self.assertEqual(walk(self.tmp), sorted(walk(self.tmp)))
    def test_empty_root(self):
        d = tempfile.mkdtemp(); self.assertEqual(walk(d), [])
    def test_none_ext(self): self.assertEqual(len(walk(self.tmp, None)), 3)
    def test_no_repo_writes(self):
        import sys
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        before = set()
        for r, ds, fs in os.walk(repo):
            if ".git" in ds: ds.remove(".git")
            if "_temp" in r or "dist" in r or "_archive" in r: continue
            for f in fs: before.add(os.path.join(r, f))
        walk(repo)
        after = set()
        for r, ds, fs in os.walk(repo):
            if ".git" in ds: ds.remove(".git")
            if "_temp" in r or "dist" in r or "_archive" in r: continue
            for f in fs: after.add(os.path.join(r, f))
        self.assertEqual(before, after)
    def test_relative(self): self.assertTrue(all(f.endswith((".py", ".txt")) for f in walk(self.tmp)))
    def test_determinism(self): self.assertEqual(walk(self.tmp, ".py"), walk(self.tmp, ".py"))
    def test_ext_txt(self): self.assertEqual(len(walk(self.tmp, ".txt")), 1)
    def test_subdir(self): self.assertTrue(any("sub" in f for f in walk(self.tmp)))
