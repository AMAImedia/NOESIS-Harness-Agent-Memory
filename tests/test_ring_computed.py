import unittest
from noesis_harness.ring_computed import RingComputed

class TestRingComputed(unittest.TestCase):
    def test_get(self): rc = RingComputed(5, lambda k: k * 2); self.assertEqual(rc.get("a"), "aa")
    def test_missing(self): self.assertIsNone(RingComputed(5).get("x"))
    def test_overflow(self): rc = RingComputed(2, lambda k: k); rc.get("a"); rc.get("b"); rc.get("c"); self.assertEqual(len(rc), 2); self.assertIsNotNone(rc.get("c"))
    def test_invalidate(self): rc = RingComputed(5, lambda k: k); rc.get("a"); self.assertTrue(rc.invalidate("a")); self.assertIsNone(rc.get("a"))
    def test_clear(self): rc = RingComputed(5, lambda k: k); rc.get("a"); rc.get("b"); self.assertEqual(rc.clear(), 2); self.assertEqual(len(rc), 0)
    def test_len(self): rc = RingComputed(5, lambda k: k); rc.get("a"); rc.get("b"); self.assertEqual(len(rc), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingComputed(0)
    def test_deterministic(self): rc = RingComputed(5, lambda k: 5); self.assertEqual(rc.get("a"), rc.get("a"))
    def test_many(self): rc = RingComputed(10, lambda k: k); [rc.get(f"k{i}") for i in range(10)]; self.assertTrue(rc.full())
    def test_no_compute(self): self.assertIsNone(RingComputed(5).get("x"))
