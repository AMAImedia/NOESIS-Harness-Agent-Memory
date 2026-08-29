import unittest
from noesis_harness.ring_dedup import RingDedup

class TestRingDedup(unittest.TestCase):
    def test_add(self): r = RingDedup(5); self.assertTrue(r.add(1))
    def test_duplicate(self): r = RingDedup(5); r.add(1); self.assertFalse(r.add(1))
    def test_overflow(self): r = RingDedup(3); r.add(1); r.add(2); r.add(3); r.add(4); self.assertEqual(len(r), 3); self.assertTrue(r.contains(4))
    def test_contains(self): r = RingDedup(5); r.add(1); self.assertTrue(r.contains(1)); self.assertFalse(r.contains(2))
    def test_empty(self): r = RingDedup(3); self.assertTrue(r.empty())
    def test_full(self): r = RingDedup(2); r.add(1); r.add(2); self.assertTrue(r.full())
    def test_len(self): r = RingDedup(5); r.add(1); r.add(2); self.assertEqual(len(r), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingDedup(0)
    def test_deterministic(self): r = RingDedup(5); r.add(1); self.assertTrue(r.contains(1))
    def test_many(self): r = RingDedup(10); [r.add(i) for i in range(10)]; self.assertTrue(r.full())
