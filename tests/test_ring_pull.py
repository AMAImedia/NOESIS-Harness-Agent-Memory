import unittest
from noesis_harness.ring_pull import RingPull

class TestRingPull(unittest.TestCase):
    def test_pull(self): rp = RingPull(5); self.assertEqual(rp.pull("a", 1), 1)
    def test_existing(self): rp = RingPull(5); rp.pull("a", 1); self.assertEqual(rp.pull("a", 2), 2)
    def test_overflow(self): rp = RingPull(2); rp.pull("a", 1); rp.pull("b", 2); rp.pull("c", 3); self.assertEqual(len(rp), 2); self.assertIsNotNone(rp.get("c"))
    def test_get(self): rp = RingPull(5); rp.set("k", 1); self.assertEqual(rp.get("k"), 1)
    def test_get_default(self): self.assertEqual(RingPull(5).get("x", 5), 5)
    def test_invalidate(self): rp = RingPull(5); rp.set("a", 1); self.assertTrue(rp.invalidate("a")); self.assertIsNone(rp.get("a"))
    def test_clear(self): rp = RingPull(5); rp.set("a", 1); rp.set("b", 2); self.assertEqual(rp.clear(), 2); self.assertEqual(len(rp), 0)
    def test_len(self): rp = RingPull(5); rp.set("a", 1); rp.set("b", 2); self.assertEqual(len(rp), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingPull(0)
    def test_deterministic(self): rp = RingPull(5); rp.set("a", 1); self.assertEqual(rp.get("a"), rp.get("a"))
    def test_many(self): rp = RingPull(10); [rp.set(f"k{i}", i) for i in range(10)]; self.assertTrue(rp.full())
