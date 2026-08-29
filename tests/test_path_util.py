import os, unittest
from noesis_harness.path_util import stem, ext, join, parent, filename

class TestPathUtil(unittest.TestCase):
    def test_stem(self): self.assertEqual(stem("file.txt"), "file")
    def test_ext(self): self.assertEqual(ext("file.txt"), ".txt")
    def test_join(self): self.assertEqual(join("a", "b", "c"), os.path.join("a", "b", "c"))
    def test_parent(self): self.assertEqual(parent("/a/b/c.txt"), os.path.dirname(os.path.abspath("/a/b/c.txt")))
    def test_filename(self): self.assertEqual(filename("/a/b/c.txt"), "c.txt")
    def test_no_ext(self): self.assertEqual(stem("file"), "file")
    def test_empty_ext(self): self.assertEqual(ext("file"), "")
    def test_multiple_dots(self): self.assertEqual(stem("a.b.c"), "a.b")
    def test_dot_ext(self): self.assertEqual(ext(".gitignore"), "")
    def test_determinism(self): self.assertEqual(stem("x.txt"), stem("x.txt"))
