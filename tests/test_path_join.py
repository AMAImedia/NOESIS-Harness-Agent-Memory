import os, tempfile, unittest
from noesis_harness.path_join import safe_join

class TestPathJoin(unittest.TestCase):
    def setUp(self): self.base = tempfile.mkdtemp()
    def test_join(self):
        p = safe_join(self.base, "a", "b.txt")
        self.assertEqual(p, os.path.join(self.base, "a", "b.txt"))
    def test_flat(self): self.assertEqual(safe_join(self.base, "x"), os.path.join(self.base, "x"))
    def test_escape(self):
        with self.assertRaises(ValueError): safe_join(self.base, "..", "..", "etc")
    def test_nested_escape(self):
        with self.assertRaises(ValueError): safe_join(self.base, "sub", "..", "..", "secret")
    def test_under_base(self):
        p = safe_join(self.base, "ok"); self.assertTrue(p.startswith(os.path.abspath(self.base)))
    def test_no_repo_writes(self):
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        before = set()
        for r, ds, fs in os.walk(repo):
            if ".git" in ds: ds.remove(".git")
            if "_temp" in r or "dist" in r or "_archive" in r: continue
            for f in fs: before.add(os.path.join(r, f))
        safe_join(self.base, "x")
        after = set()
        for r, ds, fs in os.walk(repo):
            if ".git" in ds: ds.remove(".git")
            if "_temp" in r or "dist" in r or "_archive" in r: continue
            for f in fs: after.add(os.path.join(r, f))
        self.assertEqual(before, after)
    def test_single_part(self): self.assertTrue(safe_join(self.base, "f").endswith("f"))
    def test_determinism(self): self.assertEqual(safe_join(self.base, "a"), safe_join(self.base, "a"))
    def test_subdir(self):
        sub = os.path.join(self.base, "s"); os.makedirs(sub)
        self.assertEqual(safe_join(self.base, "s", "f"), os.path.join(sub, "f"))
    def test_deep(self):
        p = safe_join(self.base, "a", "b", "c", "d"); self.assertTrue(p.endswith(os.path.join("a", "b", "c", "d")))
