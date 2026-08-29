import os, tempfile, unittest
from noesis_harness.chunked_io import read_chunks, write_chunks

class TestChunkedIO(unittest.TestCase):
    def setUp(self): self.tmp = tempfile.mkdtemp()
    def test_write_read(self):
        p = os.path.join(self.tmp, "f.bin")
        write_chunks(p, iter([b"hello", b"world"]))
        data = b"".join(read_chunks(p))
        self.assertEqual(data, b"helloworld")
    def test_empty(self):
        p = os.path.join(self.tmp, "e.bin")
        write_chunks(p, iter([]))
        self.assertEqual(b"".join(read_chunks(p)), b"")
    def test_chunk_size(self):
        p = os.path.join(self.tmp, "f.bin")
        write_chunks(p, iter([b"a" * 100]))
        chunks = list(read_chunks(p, 32))
        self.assertTrue(all(len(c) <= 32 for c in chunks))
    def test_large(self):
        p = os.path.join(self.tmp, "l.bin")
        write_chunks(p, iter([b"x" * 10000]))
        self.assertEqual(len(b"".join(read_chunks(p))), 10000)
    def test_total(self):
        p = os.path.join(self.tmp, "t.bin")
        total = write_chunks(p, iter([b"a" * 10, b"b" * 20]))
        self.assertEqual(total, 30)
    def test_deterministic(self):
        p = os.path.join(self.tmp, "d.bin")
        write_chunks(p, iter([b"data"]))
        self.assertEqual(b"".join(read_chunks(p)), b"data")
    def test_many_chunks(self):
        p = os.path.join(self.tmp, "m.bin")
        write_chunks(p, iter([b"x" for _ in range(100)]))
        self.assertEqual(len(b"".join(read_chunks(p))), 100)
    def test_binary(self):
        p = os.path.join(self.tmp, "b.bin")
        data = bytes(range(256))
        write_chunks(p, iter([data]))
        self.assertEqual(b"".join(read_chunks(p)), data)
    def test_no_repo_writes(self):
        import sys
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
    def test_single_chunk(self):
        p = os.path.join(self.tmp, "s.bin")
        write_chunks(p, iter([b"only"]))
        self.assertEqual(b"".join(read_chunks(p)), b"only")
