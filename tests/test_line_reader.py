import os, tempfile, unittest
from noesis_harness.line_reader import read_lines, iter_lines

class TestLineReader(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(); self.p = os.path.join(self.tmp, "f.txt")
        open(self.p, "w", encoding="utf-8").write("a\nb\nc\n")
    def test_read(self): self.assertEqual(read_lines(self.p), ["a", "b", "c"])
    def test_iter(self): self.assertEqual(list(iter_lines(self.p)), ["a", "b", "c"])
    def test_empty(self): p = os.path.join(self.tmp, "e.txt"); open(p, "w").write(""); self.assertEqual(read_lines(p), [])
    def test_single(self): p = os.path.join(self.tmp, "s.txt"); open(p, "w").write("x\n"); self.assertEqual(read_lines(p), ["x"])
    def test_no_newline_end(self): p = os.path.join(self.tmp, "n.txt"); open(p, "w").write("line"); self.assertEqual(read_lines(p), ["line"])
    def test_no_repo_writes(self):
        import sys
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        before = set()
        for r, ds, fs in os.walk(repo):
            if ".git" in ds: ds.remove(".git")
            if "_temp" in r or "dist" in r or "_archive" in r: continue
            for f in fs: before.add(os.path.join(r, f))
        read_lines(self.p)
        after = set()
        for r, ds, fs in os.walk(repo):
            if ".git" in ds: ds.remove(".git")
            if "_temp" in r or "dist" in r or "_archive" in r: continue
            for f in fs: after.add(os.path.join(r, f))
        self.assertEqual(before, after)
    def test_determinism(self): self.assertEqual(read_lines(self.p), read_lines(self.p))
    def test_unicode(self): p = os.path.join(self.tmp, "u.txt"); open(p, "w", encoding="utf-8").write("привет\n"); self.assertEqual(read_lines(p), ["привет"])
    def test_blank_lines(self): p = os.path.join(self.tmp, "b.txt"); open(p, "w").write("a\n\nb\n"); self.assertEqual(read_lines(p), ["a", "", "b"])
    def test_many(self):
        p = os.path.join(self.tmp, "m.txt"); open(p, "w").write("\n".join(str(i) for i in range(20)) + "\n")
        self.assertEqual(len(read_lines(p)), 20)
