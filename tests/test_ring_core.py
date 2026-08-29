import unittest
from noesis_harness.ring_core import RingCore

class TestRingCore(unittest.TestCase):
    def test_core(self): rc = RingCore(5); self.assertEqual(rc.core("a", 1), 1)
    def test_existing(self): rc = RingCore(5); rc.core("a", 1); self.assertEqual(rc.core("a", 2), 2)
    def test_overflow(self): rc = RingCore(2); rc.core("a", 1); rc.core("b", 2); rc.core("c", 3); self.assertEqual(len(rc), 2); self.assertIsNotNone(rc.get("c"))
    def test_get(self): rc = RingCore(5); rc.set("k", 1); self.assertEqual(rc.get("k"), 1)
    def test_get_default(self): self.assertEqual(RingCore(5).get("x", 5), 5)
    def test_invalidate(self): rc = RingCore(5); rc.set("a", 1); self.assertTrue(rc.invalidate("a")); self.assertIsNone(rc.get("a"))
    def test_clear(self): rc = RingCore(5); rc.set("a", 1); rc.set("b", 2); self.assertEqual(rc.clear(), 2); self.assertEqual(len(rc), 0)
    def test_len(self): rc = RingCore(5); rc.set("a", 1); rc.set("b", 2); self.assertEqual(len(rc), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingCore(0)
    def test_deterministic(self): rc = RingCore(5); rc.set("a", 1); self.assertEqual(rc.get("a"), rc.get("a"))
    def test_many(self): rc = RingCore(10); [rc.set(f"k{i}", i) for i in range(10)]; self.assertTrue(rc.full())
