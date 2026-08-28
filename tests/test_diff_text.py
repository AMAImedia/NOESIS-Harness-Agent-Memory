import unittest
from noesis_harness.diff_text import diff_lines

class TestDiffText(unittest.TestCase):
    def test_same(self): self.assertEqual(diff_lines(["a", "b"], ["a", "b"]), [(" ", "a"), (" ", "b")])
    def test_add(self):
        d = diff_lines(["a"], ["a", "b"]); self.assertEqual(d, [(" ", "a"), ("+", "b")])
    def test_remove(self):
        d = diff_lines(["a", "b"], ["a"]); self.assertEqual(d, [(" ", "a"), ("-", "b")])
    def test_change(self):
        d = diff_lines(["a", "x"], ["a", "y"])
        self.assertEqual(d[0], (" ", "a")); self.assertIn(("-", "x"), d); self.assertIn(("+", "y"), d)
    def test_empty(self): self.assertEqual(diff_lines([], []), [])
    def test_both_empty(self): self.assertEqual(diff_lines([], ["x"]), [("+", "x")])
    def test_determinism(self): self.assertEqual(diff_lines(["a"], ["b"]), diff_lines(["a"], ["b"]))
    def test_order(self):
        d = diff_lines(["a", "b", "c"], ["a", "c"]); self.assertEqual(d[0], (" ", "a")); self.assertIn(("-", "b"), d)
    def test_many(self):
        a = [str(i) for i in range(5)]; b = [str(i) for i in range(5, 0, -1)]
        d = diff_lines(a, b); self.assertEqual(len(d), 9)
    def test_no_crash(self): diff_lines(["x", "y", "z"], ["z", "y", "x"])
