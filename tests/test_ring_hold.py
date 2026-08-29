import unittest
from noesis_harness.ring_hold import RingHold

class TestRingHold(unittest.TestCase):
    def test_hold(self): rh = RingHold(5); self.assertEqual(rh.hold("a", 1), 1)
    def test_existing(self): rh = RingHold(5); rh.hold("a", 1); self.assertEqual(rh.hold("a", 2), 2)
    def test_overflow(self): rh = RingHold(2); rh.hold("a", 1); rh.hold("b", 2); rh.hold("c", 3); self.assertEqual(len(rh), 2); self.assertIsNotNone(rh.get("c"))
    def test_get(self): rh = RingHold(5); rh.set("k", 1); self.assertEqual(rh.get("k"), 1)
    def test_get_default(self): self.assertEqual(RingHold(5).get("x", 5), 5)
    def test_invalidate(self): rh = RingHold(5); rh.set("a", 1); self.assertTrue(rh.invalidate("a")); self.assertIsNone(rh.get("a"))
    def test_clear(self): rh = RingHold(5); rh.set("a", 1); rh.set("b", 2); self.assertEqual(rh.clear(), 2); self.assertEqual(len(rh), 0)
    def test_len(self): rh = RingHold(5); rh.set("a", 1); rh.set("b", 2); self.assertEqual(len(rh), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingHold(0)
    def test_deterministic(self): rh = RingHold(5); rh.set("a", 1); self.assertEqual(rh.get("a"), rh.get("a"))
    def test_many(self): rh = RingHold(10); [rh.set(f"k{i}", i) for i in range(10)]; self.assertTrue(rh.full())
