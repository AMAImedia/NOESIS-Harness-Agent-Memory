import unittest
from noesis_harness.ring_proxy import RingProxy

class TestRingProxy(unittest.TestCase):
    def test_get_set(self): rp = RingProxy(5); rp.set("k", 1); self.assertEqual(rp.get("k"), 1)
    def test_missing(self): self.assertIsNone(RingProxy(5).get("x"))
    def test_default(self): self.assertEqual(RingProxy(5).get("x", 5), 5)
    def test_overflow(self): rp = RingProxy(2); rp.set("a", 1); rp.set("b", 2); rp.set("c", 3); self.assertEqual(len(rp), 2); self.assertIsNotNone(rp.get("c"))
    def test_invalidate(self): rp = RingProxy(5); rp.set("a", 1); self.assertTrue(rp.invalidate("a")); self.assertIsNone(rp.get("a"))
    def test_clear(self): rp = RingProxy(5); rp.set("a", 1); rp.set("b", 2); self.assertEqual(rp.clear(), 2); self.assertEqual(len(rp), 0)
    def test_len(self): rp = RingProxy(5); rp.set("a", 1); rp.set("b", 2); self.assertEqual(len(rp), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingProxy(0)
    def test_deterministic(self): rp = RingProxy(5); rp.set("a", 1); self.assertEqual(rp.get("a"), rp.get("a"))
    def test_many(self): rp = RingProxy(10); [rp.set(f"k{i}", i) for i in range(10)]; self.assertTrue(rp.full())
