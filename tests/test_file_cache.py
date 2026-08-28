import os, tempfile, unittest
from noesis_harness.file_cache import FileCache

class TestFileCache(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(); self.p = os.path.join(self.tmp, "f.txt")
        open(self.p, "w", encoding="utf-8").write("content")
    def test_read(self): c = FileCache(); self.assertEqual(c.read(self.p), "content")
    def test_cached(self): c = FileCache(); c.read(self.p); self.assertTrue(c.cached(self.p))
    def test_not_cached(self): self.assertFalse(FileCache().cached(self.p))
    def test_size(self): c = FileCache(); c.read(self.p); self.assertEqual(c.size(), 1)
    def test_same_file(self):
        c = FileCache(); a = c.read(self.p); b = c.read(self.p); self.assertIs(a, b)
    def test_no_repo_writes(self):
        import sys
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        before = set()
        for r, ds, fs in os.walk(repo):
            if ".git" in ds: ds.remove(".git")
            if "_temp" in r or "dist" in r or "_archive" in r: continue
            for f in fs: before.add(os.path.join(r, f))
        FileCache().read(self.p)
        after = set()
        for r, ds, fs in os.walk(repo):
            if ".git" in ds: ds.remove(".git")
            if "_temp" in r or "dist" in r or "_archive" in r: continue
            for f in fs: after.add(os.path.join(r, f))
        self.assertEqual(before, after)
    def test_many(self):
        c = FileCache()
        for i in range(5):
            p = os.path.join(self.tmp, f"f{i}.txt"); open(p, "w").write(str(i)); c.read(p)
        self.assertEqual(c.size(), 5)
    def test_determinism(self): c = FileCache(); self.assertEqual(c.read(self.p), c.read(self.p))
    def test_two_files(self):
        c = FileCache(); q = os.path.join(self.tmp, "q.txt"); open(q, "w").write("z")
        self.assertEqual(c.read(self.p), "content"); self.assertEqual(c.read(q), "z")
    def test_empty_file(self):
        p = os.path.join(self.tmp, "e.txt"); open(p, "w").write(""); self.assertEqual(FileCache().read(p), "")
