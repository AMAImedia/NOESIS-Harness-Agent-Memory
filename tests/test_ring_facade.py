import unittest
from noesis_harness.ring_facade import RingFacade

class TestRingFacade(unittest.TestCase):
    def test_cache(self): rf = RingFacade(5); self.assertEqual(rf.cache("a", 1), 1)
    def test_existing(self): rf = RingFacade(5); rf.cache("a", 1); self.assertEqual(rf.cache("a", 2), 2)
    def test_overflow(self): rf = RingFacade(2); rf.cache("a", 1); rf.cache("b", 2); rf.cache("c", 3); self.assertEqual(len(rf), 2); self.assertIsNotNone(rf.get("c"))
    def test_get(self): rf = RingFacade(5); rf.set("k", 1); self.assertEqual(rf.get("k"), 1)
    def test_get_default(self): self.assertEqual(RingFacade(5).get("x", 5), 5)
    def test_invalidate(self): rf = RingFacade(5); rf.set("a", 1); self.assertTrue(rf.invalidate("a")); self.assertIsNone(rf.get("a"))
    def test_clear(self): rf = RingFacade(5); rf.set("a", 1); rf.set("b", 2); self.assertEqual(rf.clear(), 2); self.assertEqual(len(rf), 0)
    def test_len(self): rf = RingFacade(5); rf.set("a", 1); rf.set("b", 2); self.assertEqual(len(rf), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingFacade(0)
    def test_deterministic(self): rf = RingFacade(5); rf.set("a", 1); self.assertEqual(rf.get("a"), rf.get("a"))
    def test_many(self): rf = RingFacade(10); [rf.set(f"k{i}", i) for i in range(10)]; self.assertTrue(rf.full())
