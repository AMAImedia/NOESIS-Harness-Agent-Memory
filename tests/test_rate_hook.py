import time, unittest
from noesis_harness.rate_hook import RateHook

class TestRateHook(unittest.TestCase):
    def test_hook(self): rh = RateHook(10); self.assertEqual(rh.hook("a", 1), 1)
    def test_cached(self): rh = RateHook(10); rh.hook("a", 1); self.assertEqual(rh.hook("a", 2), 1)
    def test_get(self): rh = RateHook(10); rh.set("a", 1); self.assertEqual(rh.get("a"), 1)
    def test_get_default(self): self.assertEqual(RateHook(10).get("x", 5), 5)
    def test_ttl(self): rh = RateHook(0.01); rh.set("a", 1); time.sleep(0.02); self.assertIsNone(rh.get("a"))
    def test_invalidate(self): rh = RateHook(10); rh.set("a", 1); self.assertTrue(rh.invalidate("a")); self.assertFalse(rh.invalidate("a"))
    def test_clear(self): rh = RateHook(10); rh.set("a", 1); rh.set("b", 2); self.assertEqual(rh.clear(), 2); self.assertEqual(len(rh), 0)
    def test_len(self): rh = RateHook(10); rh.set("a", 1); rh.set("b", 2); self.assertEqual(len(rh), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RateHook(0)
    def test_deterministic(self): rh = RateHook(10); rh.set("a", 1); self.assertEqual(rh.get("a"), rh.get("a"))
    def test_many(self): rh = RateHook(10); [rh.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(rh), 5)
