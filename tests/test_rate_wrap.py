import time, unittest
from noesis_harness.rate_wrap import RateWrap

class TestRateWrap(unittest.TestCase):
    def test_wrap(self): rw = RateWrap(10); self.assertEqual(rw.wrap("a", 1), 1)
    def test_cached(self): rw = RateWrap(10); rw.wrap("a", 1); self.assertEqual(rw.wrap("a", 2), 1)
    def test_get(self): rw = RateWrap(10); rw.set("a", 1); self.assertEqual(rw.get("a"), 1)
    def test_get_default(self): self.assertEqual(RateWrap(10).get("x", 5), 5)
    def test_ttl(self): rw = RateWrap(0.01); rw.set("a", 1); time.sleep(0.02); self.assertIsNone(rw.get("a"))
    def test_invalidate(self): rw = RateWrap(10); rw.set("a", 1); self.assertTrue(rw.invalidate("a")); self.assertFalse(rw.invalidate("a"))
    def test_clear(self): rw = RateWrap(10); rw.set("a", 1); rw.set("b", 2); self.assertEqual(rw.clear(), 2); self.assertEqual(len(rw), 0)
    def test_len(self): rw = RateWrap(10); rw.set("a", 1); rw.set("b", 2); self.assertEqual(len(rw), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RateWrap(0)
    def test_deterministic(self): rw = RateWrap(10); rw.set("a", 1); self.assertEqual(rw.get("a"), rw.get("a"))
    def test_many(self): rw = RateWrap(10); [rw.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(rw), 5)
