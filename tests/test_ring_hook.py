import unittest
from noesis_harness.ring_hook import RingHook

class TestRingHook(unittest.TestCase):
    def test_hook(self): rh = RingHook(5); self.assertEqual(rh.hook("a", 1), 1)
    def test_existing(self): rh = RingHook(5); rh.hook("a", 1); self.assertEqual(rh.hook("a", 2), 2)
    def test_overflow(self): rh = RingHook(2); rh.hook("a", 1); rh.hook("b", 2); rh.hook("c", 3); self.assertEqual(len(rh), 2); self.assertIsNotNone(rh.get("c"))
    def test_get(self): rh = RingHook(5); rh.set("k", 1); self.assertEqual(rh.get("k"), 1)
    def test_get_default(self): self.assertEqual(RingHook(5).get("x", 5), 5)
    def test_invalidate(self): rh = RingHook(5); rh.set("a", 1); self.assertTrue(rh.invalidate("a")); self.assertIsNone(rh.get("a"))
    def test_clear(self): rh = RingHook(5); rh.set("a", 1); rh.set("b", 2); self.assertEqual(rh.clear(), 2); self.assertEqual(len(rh), 0)
    def test_len(self): rh = RingHook(5); rh.set("a", 1); rh.set("b", 2); self.assertEqual(len(rh), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingHook(0)
    def test_deterministic(self): rh = RingHook(5); rh.set("a", 1); self.assertEqual(rh.get("a"), rh.get("a"))
    def test_many(self): rh = RingHook(10); [rh.set(f"k{i}", i) for i in range(10)]; self.assertTrue(rh.full())
