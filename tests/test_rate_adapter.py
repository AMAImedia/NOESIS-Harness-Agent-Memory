import time, unittest
from noesis_harness.rate_adapter import RateAdapter

class TestRateAdapter(unittest.TestCase):
    def test_adapt(self): ra = RateAdapter(10); self.assertEqual(ra.adapt("a", 1), 1)
    def test_cached(self): ra = RateAdapter(10); ra.adapt("a", 1); self.assertEqual(ra.adapt("a", 2), 1)
    def test_get(self): ra = RateAdapter(10); ra.set("a", 1); self.assertEqual(ra.get("a"), 1)
    def test_get_default(self): self.assertEqual(RateAdapter(10).get("x", 5), 5)
    def test_ttl(self): ra = RateAdapter(0.01); ra.set("a", 1); time.sleep(0.02); self.assertIsNone(ra.get("a"))
    def test_invalidate(self): ra = RateAdapter(10); ra.set("a", 1); self.assertTrue(ra.invalidate("a")); self.assertFalse(ra.invalidate("a"))
    def test_clear(self): ra = RateAdapter(10); ra.set("a", 1); ra.set("b", 2); self.assertEqual(ra.clear(), 2); self.assertEqual(len(ra), 0)
    def test_len(self): ra = RateAdapter(10); ra.set("a", 1); ra.set("b", 2); self.assertEqual(len(ra), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RateAdapter(0)
    def test_deterministic(self): ra = RateAdapter(10); ra.set("a", 1); self.assertEqual(ra.get("a"), ra.get("a"))
    def test_many(self): ra = RateAdapter(10); [ra.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(ra), 5)
