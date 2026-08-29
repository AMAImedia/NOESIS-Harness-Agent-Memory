import unittest
from noesis_harness.ring_adapter import RingAdapter

class TestRingAdapter(unittest.TestCase):
    def test_adapt(self): ra = RingAdapter(5); self.assertEqual(ra.adapt("a", 1), 1)
    def test_existing(self): ra = RingAdapter(5); ra.adapt("a", 1); self.assertEqual(ra.adapt("a", 2), 2)
    def test_overflow(self): ra = RingAdapter(2); ra.adapt("a", 1); ra.adapt("b", 2); ra.adapt("c", 3); self.assertEqual(len(ra), 2); self.assertIsNotNone(ra.get("c"))
    def test_get(self): ra = RingAdapter(5); ra.set("k", 1); self.assertEqual(ra.get("k"), 1)
    def test_get_default(self): self.assertEqual(RingAdapter(5).get("x", 5), 5)
    def test_invalidate(self): ra = RingAdapter(5); ra.set("a", 1); self.assertTrue(ra.invalidate("a")); self.assertIsNone(ra.get("a"))
    def test_clear(self): ra = RingAdapter(5); ra.set("a", 1); ra.set("b", 2); self.assertEqual(ra.clear(), 2); self.assertEqual(len(ra), 0)
    def test_len(self): ra = RingAdapter(5); ra.set("a", 1); ra.set("b", 2); self.assertEqual(len(ra), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingAdapter(0)
    def test_deterministic(self): ra = RingAdapter(5); ra.set("a", 1); self.assertEqual(ra.get("a"), ra.get("a"))
    def test_many(self): ra = RingAdapter(10); [ra.set(f"k{i}", i) for i in range(10)]; self.assertTrue(ra.full())
