import time, unittest
from noesis_harness.rate_proxy import RateProxy

class TestRateProxy(unittest.TestCase):
    def test_get(self): rp = RateProxy(10); rp.set("a", 1); self.assertEqual(rp.get("a"), 1)
    def test_missing(self): self.assertIsNone(RateProxy(10).get("x"))
    def test_default(self): self.assertEqual(RateProxy(10).get("x", 5), 5)
    def test_ttl(self): rp = RateProxy(0.01); rp.set("a", 1); time.sleep(0.02); self.assertIsNone(rp.get("a"))
    def test_invalidate(self): rp = RateProxy(10); rp.set("a", 1); self.assertTrue(rp.invalidate("a")); self.assertFalse(rp.invalidate("a"))
    def test_clear(self): rp = RateProxy(10); rp.set("a", 1); rp.set("b", 2); self.assertEqual(rp.clear(), 2); self.assertEqual(len(rp), 0)
    def test_len(self): rp = RateProxy(10); rp.set("a", 1); rp.set("b", 2); self.assertEqual(len(rp), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RateProxy(0)
    def test_deterministic(self): rp = RateProxy(10); rp.set("a", 1); self.assertEqual(rp.get("a"), rp.get("a"))
    def test_many(self): rp = RateProxy(10); [rp.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(rp), 5)
