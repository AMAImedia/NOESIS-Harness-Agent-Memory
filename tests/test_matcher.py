import unittest
from noesis_harness.matcher import match

class TestMatcher(unittest.TestCase):
    def test_star(self): self.assertTrue(match("*", "anything"))
    def test_exact(self): self.assertTrue(match("abc", "abc")); self.assertFalse(match("abc", "ab"))
    def test_prefix(self): self.assertTrue(match("a*", "abc")); self.assertFalse(match("a*", "bc"))
    def test_suffix(self): self.assertTrue(match("*c", "abc")); self.assertFalse(match("*c", "ab"))
    def test_middle(self): self.assertTrue(match("a*c", "abc")); self.assertFalse(match("a*c", "ab"))
    def test_qmark(self): self.assertTrue(match("a?c", "abc")); self.assertFalse(match("a?c", "ac"))
    def test_multi_star(self): self.assertTrue(match("a*b*c", "axxbxxc"))
    def test_empty(self): self.assertTrue(match("", "")); self.assertFalse(match("a", ""))
    def test_no_match(self): self.assertFalse(match("x*y", "a*b"))
    def test_determinism(self): self.assertEqual(match("a*", "abc"), match("a*", "abc"))
