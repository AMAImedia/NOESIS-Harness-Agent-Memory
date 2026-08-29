import os, tempfile, unittest
from noesis_harness.chunked_write import write_chunks, write_lines

class TestChunkedWrite(unittest.TestCase):
    def setUp(self): self.tmp = tempfile.mkdtemp()
    def test_write_chunks(self):
        p = os.path.join(self.tmp, "f.bin")
        write_chunks(p, iter([b"hello", b"world"]))
        self.assertEqual(open(p, "rb").read(), b"helloworld")
    def test_write_lines(self):
        p = os.path.join(self.tmp, "f.txt")
        write_lines(p, iter(["line1", "line2"]))
        self.assertEqual(open(p).read(), "line1\nline2\n")
    def test_empty(self):
        p = os.path.join(self.tmp, "e.bin")
        write_chunks(p, iter([]))
        self.assertEqual(open(p, "rb").read(), b"")
    def test_total(self):
        p = os.path.join(self.tmp, "t.bin")
        total = write_chunks(p, iter([b"a" * 10, b"b" * 20]))
        self.assertEqual(total, 30)
    def test_lines_total(self):
        p = os.path.join(self.tmp, "l.txt")
        total = write_lines(p, iter(["a", "b", "c"]))
        self.assertEqual(total, 3)
    def test_large(self):
        p = os.path.join(self.tmp, "l.bin")
        write_chunks(p, iter([b"x" * 10000]))
        self.assertEqual(len(open(p, "rb").read()), 10000)
    def test_deterministic(self):
        p = os.path.join(self.tmp, "d.bin")
        write_chunks(p, iter([b"data"]))
        self.assertEqual(open(p, "rb").read(), b"data")
    def test_many(self):
        p = os.path.join(self.tmp, "m.bin")
        write_chunks(p, iter([b"x" for _ in range(100)]))
        self.assertEqual(len(open(p, "rb").read()), 100)
    def test_no_repo_writes(self):
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        before = set()
        for r, ds, fs in os.walk(repo):
            if ".git" in ds: ds.remove(".git")
            if "_temp" in r or "dist" in r or "_archive" in r: continue
            for f in fs: before.add(os.path.join(r, f))
        p = os.path.join(self.tmp, "x"); write_chunks(p, iter([b"y"]))
        after = set()
        for r, ds, fs in os.walk(repo):
            if ".git" in ds: ds.remove(".git")
            if "_temp" in r or "dist" in r or "_archive" in r: continue
            for f in fs: after.add(os.path.join(r, f))
        self.assertEqual(before, after)
    def test_single(self):
        p = os.path.join(self.tmp, "s.bin")
        write_chunks(p, iter([b"only"]))
        self.assertEqual(open(p, "rb").read(), b"only")
