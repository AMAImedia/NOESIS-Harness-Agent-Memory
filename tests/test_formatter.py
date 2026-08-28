import unittest
from noesis_harness.formatter import truncate, pad

class TestFormatter(unittest.TestCase):
    def test_truncate(self): self.assertEqual(truncate("hello world", 5), "he...")
    def test_no_truncate(self): self.assertEqual(truncate("hi", 10), "hi")
    def test_invalid_width(self):
        with self.assertRaises(ValueError): truncate("x", -1)
    def test_short_suffix(self): self.assertEqual(truncate("hello", 2, ".."), "he")
    def test_pad_left(self): self.assertEqual(pad("a", 3, "left"), "a  ")
    def test_pad_right(self): self.assertEqual(pad("a", 3, "right"), "  a")
    def test_pad_center(self): self.assertEqual(pad("a", 3, "center"), " a ")
    def test_invalid_align(self):
        with self.assertRaises(ValueError): pad("a", 3, "mid")
    def test_pad_over(self): self.assertEqual(pad("abcd", 2), "ab")
    def test_determinism(self): self.assertEqual(truncate("hello", 3), truncate("hello", 3))
