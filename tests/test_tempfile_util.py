import os, unittest
from noesis_harness.tempfile_util import make_temp_dir, make_temp_file

class TestTempfileUtil(unittest.TestCase):
    def test_dir(self):
        import tempfile as t
        base = t.mkdtemp()
        d = make_temp_dir(base); self.assertTrue(os.path.isdir(d)); self.assertTrue(d.startswith(base))
    def test_file(self):
        import tempfile as t
        base = t.mkdtemp()
        p = make_temp_file(base); self.assertTrue(os.path.isfile(p))
    def test_suffix(self):
        import tempfile as t
        base = t.mkdtemp()
        p = make_temp_file(base, ".log"); self.assertTrue(p.endswith(".log"))
    def test_no_repo_writes(self):
        import tempfile as t
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        before = set()
        for r, ds, fs in os.walk(repo):
            if ".git" in ds: ds.remove(".git")
            if "_temp" in r or "dist" in r or "_archive" in r: continue
            for f in fs: before.add(os.path.join(r, f))
        make_temp_file(t.mkdtemp())
        after = set()
        for r, ds, fs in os.walk(repo):
            if ".git" in ds: ds.remove(".git")
            if "_temp" in r or "dist" in r or "_archive" in r: continue
            for f in fs: after.add(os.path.join(r, f))
        self.assertEqual(before, after)
    def test_dir_unique(self):
        import tempfile as t
        base = t.mkdtemp()
        self.assertNotEqual(make_temp_dir(base), make_temp_dir(base))
    def test_file_unique(self):
        import tempfile as t
        base = t.mkdtemp()
        self.assertNotEqual(make_temp_file(base), make_temp_file(base))
    def test_dir_exists(self):
        import tempfile as t
        base = t.mkdtemp()
        self.assertTrue(os.path.isdir(make_temp_dir(base)))
    def test_file_writable(self):
        import tempfile as t
        base = t.mkdtemp()
        p = make_temp_file(base); open(p, "w").write("x"); self.assertEqual(open(p).read(), "x")
    def test_many(self):
        import tempfile as t
        base = t.mkdtemp()
        for _ in range(5): make_temp_file(base)
    def test_determinism_shape(self):
        import tempfile as t
        base = t.mkdtemp()
        self.assertTrue(os.path.isfile(make_temp_file(base)))
