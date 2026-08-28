import unittest
from noesis_harness.indent import indent

class TestIndent(unittest.TestCase):
    def test_one(self): self.assertEqual(indent("a"), "  a")
    def test_level(self): self.assertEqual(indent("a", " ", 2), "  a")
    def test_multi(self): self.assertEqual(indent("a\nb"), "  a\n  b")
    def test_empty_lines(self): self.assertEqual(indent("a\n\nb"), "  a\n\n  b")
    def test_custom_prefix(self): self.assertEqual(indent("a", ">", 1), ">a")
    def test_level0(self): self.assertEqual(indent("a", " ", 0), "a")
    def test_invalid(self):
        with self.assertRaises(ValueError): indent("a", " ", -1)
    def test_blank(self): self.assertEqual(indent("", " ", 1), "")
    def test_determinism(self): self.assertEqual(indent("x"), indent("x"))
    def test_single_line(self): self.assertEqual(indent("hello", "  ", 3), "      hello")
