import unittest
from noesis_harness.bool_util import to_bool, negate, all_true, any_true

class TestBoolUtil(unittest.TestCase):
    def test_bool(self): self.assertTrue(to_bool(True)); self.assertFalse(to_bool(False))
    def test_string(self): self.assertTrue(to_bool("true")); self.assertFalse(to_bool("false"))
    def test_int(self): self.assertTrue(to_bool(1)); self.assertFalse(to_bool(0))
    def test_float(self): self.assertTrue(to_bool(1.0)); self.assertFalse(to_bool(0.0))
    def test_none(self): self.assertFalse(to_bool(None))
    def test_negate(self): self.assertFalse(negate(True)); self.assertTrue(negate(False))
    def test_all_true(self): self.assertTrue(all_true([True, True])); self.assertFalse(all_true([True, False]))
    def test_any_true(self): self.assertTrue(any_true([False, True])); self.assertFalse(any_true([False, False]))
    def test_deterministic(self): self.assertEqual(to_bool("yes"), to_bool("yes"))
    def test_yes(self): self.assertTrue(to_bool("YES")); self.assertTrue(to_bool("on"))
