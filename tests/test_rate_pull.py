import time, unittest
from noesis_harness.rate_pull import RatePull

class TestRatePull(unittest.TestCase):
    def test_pull(self): rp = RatePull(10); self.assertEqual(rp.pull("a", 1), 1)
    def test_cached(self): rp = RatePull(10); rp.pull("a", 1); self.assertEqual(rp.pull("a", 2), 1)
    def test_get(self): rp = RatePull(10); rp.set("a", 1); self.assertEqual(rp.get("a"), 1)
    def test_get_default(self): self.assertEqual(RatePull(10).get("x", 5), 5)
    def test_ttl(self): rp = RatePull(0.01); rp.set("a", 1); time.sleep(0.02); self.assertIsNone(rp.get("a"))
    def test_invalidate(self): rp = RatePull(10); rp.set("a", 1); self.assertTrue(rp.invalidate("a")); self.assertFalse(rp.invalidate("a"))
    def test_clear(self): rp = RatePull(10); rp.set("a", 1); rp.set("b", 2); self.assertEqual(rp.clear(), 2); self.assertEqual(len(rp), 0)
    def test_len(self): rp = RatePull(10); rp.set("a", 1); rp.set("b", 2); self.assertEqual(len(rp), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RatePull(0)
    def test_deterministic(self): rp = RatePull(10); rp.set("a", 1); self.assertEqual(rp.get("a"), rp.get("a"))
    def test_many(self): rp = RatePull(10); [rp.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(rp), 5)
