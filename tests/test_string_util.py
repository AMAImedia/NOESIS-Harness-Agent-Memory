import unittest
from noesis_harness.string_util import is_empty, reverse, count_char, is_palindrome, title_case

class TestStringUtil(unittest.TestCase):
    def test_empty(self): self.assertTrue(is_empty("")); self.assertTrue(is_empty("  "))
    def test_not_empty(self): self.assertFalse(is_empty("a"))
    def test_reverse(self): self.assertEqual(reverse("abc"), "cba")
    def test_count(self): self.assertEqual(count_char("aab", "a"), 2)
    def test_palindrome(self): self.assertTrue(is_palindrome("racecar"))
    def test_not_palindrome(self): self.assertFalse(is_palindrome("hello"))
    def test_title(self): self.assertEqual(title_case("hello world"), "Hello World")
    def test_deterministic(self): self.assertEqual(reverse("abc"), reverse("abc"))
    def test_empty_reverse(self): self.assertEqual(reverse(""), "")
    def test_palindrome_spaces(self): self.assertTrue(is_palindrome("A man a plan a canal Panama"))
