import time, unittest
from noesis_harness.rate_facade import RateFacade

class TestRateFacade(unittest.TestCase):
    def test_cache(self): rf = RateFacade(10); self.assertEqual(rf.cache("a", 1), 1)
    def test_cached(self): rf = RateFacade(10); rf.cache("a", 1); self.assertEqual(rf.cache("a", 2), 1)
    def test_get(self): rf = RateFacade(10); rf.set("a", 1); self.assertEqual(rf.get("a"), 1)
    def test_get_default(self): self.assertEqual(RateFacade(10).get("x", 5), 5)
    def test_ttl(self): rf = RateFacade(0.01); rf.set("a", 1); time.sleep(0.02); self.assertIsNone(rf.get("a"))
    def test_invalidate(self): rf = RateFacade(10); rf.set("a", 1); self.assertTrue(rf.invalidate("a")); self.assertFalse(rf.invalidate("a"))
    def test_clear(self): rf = RateFacade(10); rf.set("a", 1); rf.set("b", 2); self.assertEqual(rf.clear(), 2); self.assertEqual(len(rf), 0)
    def test_len(self): rf = RateFacade(10); rf.set("a", 1); rf.set("b", 2); self.assertEqual(len(rf), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RateFacade(0)
    def test_deterministic(self): rf = RateFacade(10); rf.set("a", 1); self.assertEqual(rf.get("a"), rf.get("a"))
    def test_many(self): rf = RateFacade(10); [rf.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(rf), 5)
