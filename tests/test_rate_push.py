import time, unittest
from noesis_harness.rate_push import RatePush

class TestRatePush(unittest.TestCase):
    def test_push(self): rp = RatePush(10); self.assertEqual(rp.push("a", 1), 1)
    def test_cached(self): rp = RatePush(10); rp.push("a", 1); self.assertEqual(rp.push("a", 2), 1)
    def test_get(self): rp = RatePush(10); rp.set("a", 1); self.assertEqual(rp.get("a"), 1)
    def test_get_default(self): self.assertEqual(RatePush(10).get("x", 5), 5)
    def test_ttl(self): rp = RatePush(0.01); rp.set("a", 1); time.sleep(0.02); self.assertIsNone(rp.get("a"))
    def test_invalidate(self): rp = RatePush(10); rp.set("a", 1); self.assertTrue(rp.invalidate("a")); self.assertFalse(rp.invalidate("a"))
    def test_clear(self): rp = RatePush(10); rp.set("a", 1); rp.set("b", 2); self.assertEqual(rp.clear(), 2); self.assertEqual(len(rp), 0)
    def test_len(self): rp = RatePush(10); rp.set("a", 1); rp.set("b", 2); self.assertEqual(len(rp), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RatePush(0)
    def test_deterministic(self): rp = RatePush(10); rp.set("a", 1); self.assertEqual(rp.get("a"), rp.get("a"))
    def test_many(self): rp = RatePush(10); [rp.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(rp), 5)
