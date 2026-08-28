import unittest
from noesis_harness.timeout import Deadline

class TestDeadline(unittest.TestCase):
    def test_not_expired(self): d = Deadline(10, now=0); self.assertFalse(d.expired(now=5))
    def test_expired(self): d = Deadline(5, now=0); self.assertTrue(d.expired(now=5)); self.assertTrue(d.expired(now=6))
    def test_remaining(self): d = Deadline(10, now=0); self.assertAlmostEqual(d.remaining(now=3), 7)
    def test_remaining_expired(self): d = Deadline(5, now=0); self.assertEqual(d.remaining(now=10), 0.0)
    def test_zero(self): d = Deadline(0, now=0); self.assertTrue(d.expired(now=0))
    def test_invalid(self):
        with self.assertRaises(ValueError): Deadline(-1)
    def test_determinism(self): a = Deadline(5, now=0); b = Deadline(5, now=0); self.assertEqual(a.expired(now=3), b.expired(now=3))
    def test_boundary(self): d = Deadline(5, now=0); self.assertTrue(d.expired(now=5))
    def test_remaining_boundary(self): d = Deadline(5, now=0); self.assertEqual(d.remaining(now=5), 0.0)
    def test_default_now(self): d = Deadline(100); self.assertFalse(d.expired())
