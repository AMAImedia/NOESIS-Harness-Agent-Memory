import unittest
from noesis_harness.ring_halt import RingHalt

class TestRingHalt(unittest.TestCase):
    def test_halt(self): rh = RingHalt(5); self.assertEqual(rh.halt("a", 1), 1)
    def test_existing(self): rh = RingHalt(5); rh.halt("a", 1); self.assertEqual(rh.halt("a", 2), 2)
    def test_overflow(self): rh = RingHalt(2); rh.halt("a", 1); rh.halt("b", 2); rh.halt("c", 3); self.assertEqual(len(rh), 2); self.assertIsNotNone(rh.get("c"))
    def test_get(self): rh = RingHalt(5); rh.set("k", 1); self.assertEqual(rh.get("k"), 1)
    def test_get_default(self): self.assertEqual(RingHalt(5).get("x", 5), 5)
    def test_invalidate(self): rh = RingHalt(5); rh.set("a", 1); self.assertTrue(rh.invalidate("a")); self.assertIsNone(rh.get("a"))
    def test_clear(self): rh = RingHalt(5); rh.set("a", 1); rh.set("b", 2); self.assertEqual(rh.clear(), 2); self.assertEqual(len(rh), 0)
    def test_len(self): rh = RingHalt(5); rh.set("a", 1); rh.set("b", 2); self.assertEqual(len(rh), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingHalt(0)
    def test_deterministic(self): rh = RingHalt(5); rh.set("a", 1); self.assertEqual(rh.get("a"), rh.get("a"))
    def test_many(self): rh = RingHalt(10); [rh.set(f"k{i}", i) for i in range(10)]; self.assertTrue(rh.full())
