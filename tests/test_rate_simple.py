import time, unittest
from noesis_harness.rate_simple import RateSimple

class TestRateSimple(unittest.TestCase):
    def test_remember(self): rs = RateSimple(10); self.assertEqual(rs.remember("a", 1), 1)
    def test_cached(self): rs = RateSimple(10); rs.remember("a", 1); self.assertEqual(rs.remember("a", 2), 1)
    def test_get(self): rs = RateSimple(10); rs.set("a", 1); self.assertEqual(rs.get("a"), 1)
    def test_get_default(self): self.assertEqual(RateSimple(10).get("x", 5), 5)
    def test_ttl(self): rs = RateSimple(0.01); rs.set("a", 1); time.sleep(0.02); self.assertIsNone(rs.get("a"))
    def test_invalidate(self): rs = RateSimple(10); rs.set("a", 1); self.assertTrue(rs.invalidate("a")); self.assertFalse(rs.invalidate("a"))
    def test_clear(self): rs = RateSimple(10); rs.set("a", 1); rs.set("b", 2); self.assertEqual(rs.clear(), 2); self.assertEqual(len(rs), 0)
    def test_len(self): rs = RateSimple(10); rs.set("a", 1); rs.set("b", 2); self.assertEqual(len(rs), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RateSimple(0)
    def test_deterministic(self): rs = RateSimple(10); rs.set("a", 1); self.assertEqual(rs.get("a"), rs.get("a"))
    def test_many(self): rs = RateSimple(10); [rs.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(rs), 5)
