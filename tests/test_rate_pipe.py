import time, unittest
from noesis_harness.rate_pipe import RatePipe

class TestRatePipe(unittest.TestCase):
    def test_pipe(self): rp = RatePipe(10); self.assertEqual(rp.pipe("a", 1), 1)
    def test_cached(self): rp = RatePipe(10); rp.pipe("a", 1); self.assertEqual(rp.pipe("a", 2), 1)
    def test_get(self): rp = RatePipe(10); rp.set("a", 1); self.assertEqual(rp.get("a"), 1)
    def test_get_default(self): self.assertEqual(RatePipe(10).get("x", 5), 5)
    def test_ttl(self): rp = RatePipe(0.01); rp.set("a", 1); time.sleep(0.02); self.assertIsNone(rp.get("a"))
    def test_invalidate(self): rp = RatePipe(10); rp.set("a", 1); self.assertTrue(rp.invalidate("a")); self.assertFalse(rp.invalidate("a"))
    def test_clear(self): rp = RatePipe(10); rp.set("a", 1); rp.set("b", 2); self.assertEqual(rp.clear(), 2); self.assertEqual(len(rp), 0)
    def test_len(self): rp = RatePipe(10); rp.set("a", 1); rp.set("b", 2); self.assertEqual(len(rp), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RatePipe(0)
    def test_deterministic(self): rp = RatePipe(10); rp.set("a", 1); self.assertEqual(rp.get("a"), rp.get("a"))
    def test_many(self): rp = RatePipe(10); [rp.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(rp), 5)
