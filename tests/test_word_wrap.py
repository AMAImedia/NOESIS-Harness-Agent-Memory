import unittest
from noesis_harness.word_wrap import wrap

class TestWordWrap(unittest.TestCase):
    def test_wrap(self): self.assertEqual(wrap("a b c", 3), ["a b", "c"])
    def test_single(self): self.assertEqual(wrap("hello", 10), ["hello"])
    def test_empty(self): self.assertEqual(wrap("", 5), [])
    def test_width_one(self): self.assertEqual(wrap("a b", 1), ["a", "b"])
    def test_long_word(self): self.assertEqual(wrap("abcdef", 3), ["abcdef"])
    def test_invalid(self):
        with self.assertRaises(ValueError): wrap("x", 0)
    def test_no_break(self): self.assertEqual(wrap("one two three", 100), ["one two three"])
    def test_determinism(self): self.assertEqual(wrap("the quick fox", 5), wrap("the quick fox", 5))
    def test_many(self):
        out = wrap("word " * 10, 10); self.assertTrue(all(len(l) <= 12 for l in out))
    def test_exact(self): self.assertEqual(wrap("ab cd", 5), ["ab cd"])
