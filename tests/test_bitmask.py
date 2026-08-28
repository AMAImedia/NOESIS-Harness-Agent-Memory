import unittest
from noesis_harness.bitmask import set_bit, clear_bit, has_bit, toggle_bit

class TestBitmask(unittest.TestCase):
    def test_set(self): self.assertEqual(set_bit(0, 0), 1)
    def test_set2(self): self.assertEqual(set_bit(0, 2), 4)
    def test_has(self): self.assertTrue(has_bit(5, 0)); self.assertFalse(has_bit(5, 1))
    def test_clear(self): self.assertEqual(clear_bit(5, 2), 1)
    def test_toggle_on(self): self.assertEqual(toggle_bit(0, 1), 2)
    def test_toggle_off(self): self.assertEqual(toggle_bit(3, 0), 2)
    def test_set_idempotent(self): self.assertEqual(set_bit(1, 0), 1)
    def test_clear_missing(self): self.assertEqual(clear_bit(1, 1), 1)
    def test_determinism(self): self.assertEqual(set_bit(0, 3), set_bit(0, 3))
    def test_all(self): m = 0; m = set_bit(m, 0); m = set_bit(m, 1); self.assertEqual(m, 3); self.assertTrue(has_bit(m, 1)); m = clear_bit(m, 0); self.assertFalse(has_bit(m, 0))
