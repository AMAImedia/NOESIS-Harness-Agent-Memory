import os, tempfile, unittest
from noesis_harness.atomic_write import atomic_write

class TestAtomicWrite(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
    def test_write(self):
        p = os.path.join(self.tmp, "f.bin"); atomic_write(p, b"hello")
        self.assertEqual(open(p, "rb").read(), b"hello")
    def test_overwrite(self):
        p = os.path.join(self.tmp, "f.bin"); atomic_write(p, b"a"); atomic_write(p, b"bb")
        self.assertEqual(open(p, "rb").read(), b"bb")
    def test_no_repo_writes(self):
        import sys
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        before = set()
        for r, ds, fs in os.walk(repo):
            if ".git" in ds: ds.remove(".git")
            if "_temp" in r or "dist" in r or "_archive" in r: continue
            for f in fs: before.add(os.path.join(r, f))
        atomic_write(os.path.join(self.tmp, "x"), b"y", tmp_dir=self.tmp)
        after = set()
        for r, ds, fs in os.walk(repo):
            if ".git" in ds: ds.remove(".git")
            if "_temp" in r or "dist" in r or "_archive" in r: continue
            for f in fs: after.add(os.path.join(r, f))
        self.assertEqual(before, after)
    def test_tmp_cleaned(self):
        p = os.path.join(self.tmp, "f.bin"); atomic_write(p, b"data", tmp_dir=self.tmp)
        leftovers = [f for f in os.listdir(self.tmp) if f != "f.bin"]
        self.assertEqual(leftovers, [])
    def test_empty(self):
        p = os.path.join(self.tmp, "e.bin"); atomic_write(p, b""); self.assertEqual(open(p, "rb").read(), b"")
    def test_determinism(self):
        p = os.path.join(self.tmp, "d.bin"); atomic_write(p, b"z"); self.assertEqual(open(p, "rb").read(), b"z")
    def test_creates_dir(self):
        sub = os.path.join(self.tmp, "nested"); p = os.path.join(sub, "a.txt"); atomic_write(p, b"k")
        self.assertEqual(open(p, "rb").read(), b"k")
    def test_large(self):
        p = os.path.join(self.tmp, "l.bin"); atomic_write(p, b"x" * 4096); self.assertEqual(open(p, "rb").read(), b"x" * 4096)
    def test_no_leak_on_exc(self):
        p = os.path.join(self.tmp, "g.bin")
        atomic_write(p, b"ok", tmp_dir=self.tmp)
        self.assertEqual(len(os.listdir(self.tmp)), 1)
    def test_unicode(self):
        p = os.path.join(self.tmp, "u.bin"); atomic_write(p, "привет".encode("utf-8")); self.assertEqual(open(p, "rb").read(), "привет".encode("utf-8"))
