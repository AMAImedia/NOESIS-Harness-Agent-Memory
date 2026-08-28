import unittest
from noesis_harness.glob_util import match, filter

class TestGlobUtil(unittest.TestCase):
    def test_star(self): self.assertTrue(match("*.py", "a.py")); self.assertFalse(match("*.py", "a.txt"))
    def test_question(self): self.assertTrue(match("a?c", "abc")); self.assertFalse(match("a?c", "ac"))
    def test_char_class(self): self.assertTrue(match("file[0-9].log", "file3.log"))
    def test_filter(self): self.assertEqual(filter(["a.py", "b.txt", "c.py"], "*.py"), ["a.py", "c.py"])
    def test_exact(self): self.assertTrue(match("exact", "exact"))
    def test_empty(self): self.assertEqual(filter([], "*.py"), [])
    def test_multi(self): self.assertEqual(filter(["x.md", "y.md", "z.txt"], "*.md"), ["x.md", "y.md"])
    def test_determinism(self): self.assertEqual(match("*.txt", "a.txt"), match("*.txt", "a.txt"))
    def test_dir_pattern(self): self.assertTrue(match("src/*.py", "src/a.py"))
    def test_no_match(self): self.assertFalse(match("a*", "bbb"))
