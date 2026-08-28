import unittest
from noesis_harness.duration import parse

class TestDuration(unittest.TestCase):
    def test_h(self): self.assertEqual(parse("1h"), 3600)
    def test_m(self): self.assertEqual(parse("30m"), 1800)
    def test_compound(self): self.assertEqual(parse("1h30m"), 5400)
    def test_s(self): self.assertEqual(parse("45s"), 45)
    def test_d(self): self.assertEqual(parse("1d"), 86400)
    def test_ms(self): self.assertEqual(parse("500ms"), 0.5)
    def test_empty(self):
        with self.assertRaises(ValueError): parse("")
    def test_bad_unit(self):
        with self.assertRaises(ValueError): parse("10x")
    def test_decimal(self): self.assertEqual(parse("1.5h"), 5400)
    def test_determinism(self): self.assertEqual(parse("2h"), parse("2h"))
