import unittest
from noesis_harness.parse_bool import parse_bool

class TestParseBool(unittest.TestCase):
    def test_true(self): self.assertTrue(parse_bool("true"))
    def test_false(self): self.assertFalse(parse_bool("false"))
    def test_yes(self): self.assertTrue(parse_bool("YES"))
    def test_no(self): self.assertFalse(parse_bool("n"))
    def test_default(self): self.assertEqual(parse_bool("maybe", True), True); self.assertEqual(parse_bool("maybe", False), False)
    def test_none(self): self.assertEqual(parse_bool(None, True), True)
    def test_on(self): self.assertTrue(parse_bool("on"))
    def test_off(self): self.assertFalse(parse_bool("off"))
    def test_empty(self): self.assertEqual(parse_bool("", True), True)
    def test_int_str(self): self.assertTrue(parse_bool("1")); self.assertFalse(parse_bool("0"))
    def test_determinism(self): self.assertEqual(parse_bool("True"), parse_bool("true"))
