import unittest
from noesis_harness.ring_push import RingPush

class TestRingPush(unittest.TestCase):
    def test_push(self): rp = RingPush(5); self.assertEqual(rp.push("a", 1), 1)
    def test_existing(self): rp = RingPush(5); rp.push("a", 1); self.assertEqual(rp.push("a", 2), 2)
    def test_overflow(self): rp = RingPush(2); rp.push("a", 1); rp.push("b", 2); rp.push("c", 3); self.assertEqual(len(rp), 2); self.assertIsNotNone(rp.get("c"))
    def test_get(self): rp = RingPush(5); rp.set("k", 1); self.assertEqual(rp.get("k"), 1)
    def test_get_default(self): self.assertEqual(RingPush(5).get("x", 5), 5)
    def test_invalidate(self): rp = RingPush(5); rp.set("a", 1); self.assertTrue(rp.invalidate("a")); self.assertIsNone(rp.get("a"))
    def test_clear(self): rp = RingPush(5); rp.set("a", 1); rp.set("b", 2); self.assertEqual(rp.clear(), 2); self.assertEqual(len(rp), 0)
    def test_len(self): rp = RingPush(5); rp.set("a", 1); rp.set("b", 2); self.assertEqual(len(rp), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingPush(0)
    def test_deterministic(self): rp = RingPush(5); rp.set("a", 1); self.assertEqual(rp.get("a"), rp.get("a"))
    def test_many(self): rp = RingPush(10); [rp.set(f"k{i}", i) for i in range(10)]; self.assertTrue(rp.full())
