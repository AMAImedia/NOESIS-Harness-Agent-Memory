import unittest
from noesis_harness.ring_flush import RingFlush

class TestRingFlush(unittest.TestCase):
    def test_flush(self): rf = RingFlush(5); self.assertEqual(rf.flush("a", 1), 1)
    def test_existing(self): rf = RingFlush(5); rf.flush("a", 1); self.assertEqual(rf.flush("a", 2), 2)
    def test_overflow(self): rf = RingFlush(2); rf.flush("a", 1); rf.flush("b", 2); rf.flush("c", 3); self.assertEqual(len(rf), 2); self.assertIsNotNone(rf.get("c"))
    def test_get(self): rf = RingFlush(5); rf.set("k", 1); self.assertEqual(rf.get("k"), 1)
    def test_get_default(self): self.assertEqual(RingFlush(5).get("x", 5), 5)
    def test_invalidate(self): rf = RingFlush(5); rf.set("a", 1); self.assertTrue(rf.invalidate("a")); self.assertIsNone(rf.get("a"))
    def test_clear(self): rf = RingFlush(5); rf.set("a", 1); rf.set("b", 2); self.assertEqual(rf.clear(), 2); self.assertEqual(len(rf), 0)
    def test_len(self): rf = RingFlush(5); rf.set("a", 1); rf.set("b", 2); self.assertEqual(len(rf), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingFlush(0)
    def test_deterministic(self): rf = RingFlush(5); rf.set("a", 1); self.assertEqual(rf.get("a"), rf.get("a"))
    def test_many(self): rf = RingFlush(10); [rf.set(f"k{i}", i) for i in range(10)]; self.assertTrue(rf.full())
