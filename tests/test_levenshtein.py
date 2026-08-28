import unittest
from noesis_harness.levenshtein import distance

class TestLevenshtein(unittest.TestCase):
    def test_same(self): self.assertEqual(distance("abc", "abc"), 0)
    def test_empty(self): self.assertEqual(distance("", "abc"), 3); self.assertEqual(distance("abc", ""), 3)
    def test_one_sub(self): self.assertEqual(distance("abc", "abd"), 1)
    def test_one_ins(self): self.assertEqual(distance("ac", "abc"), 1)
    def test_one_del(self): self.assertEqual(distance("abc", "ac"), 1)
    def test_diff(self): self.assertEqual(distance("kitten", "sitting"), 3)
    def test_full(self): self.assertEqual(distance("abc", "xyz"), 3)
    def test_determinism(self): self.assertEqual(distance("foo", "bar"), distance("foo", "bar"))
    def test_symmetric(self): self.assertEqual(distance("abc", "ab"), distance("ab", "abc"))
    def test_long(self): self.assertEqual(distance("a" * 10, "a" * 10 + "b"), 1)
