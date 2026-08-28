import unittest
from noesis_harness.parse_int import parse_int

class TestParseInt(unittest.TestCase):
    def test_basic(self): self.assertEqual(parse_int("42"), 42)
    def test_default(self): self.assertEqual(parse_int("abc", 7), 7)
    def test_empty(self): self.assertEqual(parse_int("", 3), 3)
    def test_lo(self): self.assertEqual(parse_int("-5", 0, lo=0), 0)
    def test_hi(self): self.assertEqual(parse_int("100", 0, hi=50), 50)
    def test_none(self): self.assertEqual(parse_int(None, 9), 9)
    def test_within(self): self.assertEqual(parse_int("5", 0, lo=0, hi=10), 5)
    def test_neg(self): self.assertEqual(parse_int("-9"), -9)
    def test_float_str(self): self.assertEqual(parse_int("3.5", 0), 0)
    def test_determinism(self): self.assertEqual(parse_int("10"), parse_int("10"))
