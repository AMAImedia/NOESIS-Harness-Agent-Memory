import unittest
from noesis_harness.throttle import Throttle

class TestThrottle(unittest.TestCase):
    def test_allow_first(self): self.assertTrue(Throttle(1).allow(now=0))
    def test_deny_within(self): t = Throttle(5); t.allow(now=0); self.assertFalse(t.allow(now=2))
    def test_allow_after(self): t = Throttle(5); t.allow(now=0); self.assertTrue(t.allow(now=5))
    def test_zero_interval(self): t = Throttle(0); self.assertTrue(t.allow(now=0)); self.assertTrue(t.allow(now=0))
    def test_invalid(self):
        with self.assertRaises(ValueError): Throttle(-1)
    def test_determinism(self): a = Throttle(5); b = Throttle(5); a.allow(now=0); b.allow(now=0); self.assertEqual(a.allow(now=2), b.allow(now=2))
    def test_many(self): t = Throttle(1); self.assertTrue(t.allow(now=0)); self.assertFalse(t.allow(now=0.5)); self.assertTrue(t.allow(now=1))
    def test_default_now(self): t = Throttle(100); self.assertTrue(t.allow())
    def test_boundary(self): t = Throttle(5); t.allow(now=0); self.assertTrue(t.allow(now=5))
    def test_two(self): t = Throttle(10); t.allow(now=0); self.assertFalse(t.allow(now=5)); self.assertTrue(t.allow(now=10))
