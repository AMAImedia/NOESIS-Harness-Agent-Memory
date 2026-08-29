import time, unittest
from noesis_harness.rate_stop import RateStop

class TestRateStop(unittest.TestCase):
    def test_stop(self): rs = RateStop(10); self.assertEqual(rs.stop("a", 1), 1)
    def test_cached(self): rs = RateStop(10); rs.stop("a", 1); self.assertEqual(rs.stop("a", 2), 1)
    def test_get(self): rs = RateStop(10); rs.set("a", 1); self.assertEqual(rs.get("a"), 1)
    def test_get_default(self): self.assertEqual(RateStop(10).get("x", 5), 5)
    def test_ttl(self): rs = RateStop(0.01); rs.set("a", 1); time.sleep(0.02); self.assertIsNone(rs.get("a"))
    def test_invalidate(self): rs = RateStop(10); rs.set("a", 1); self.assertTrue(rs.invalidate("a")); self.assertFalse(rs.invalidate("a"))
    def test_clear(self): rs = RateStop(10); rs.set("a", 1); rs.set("b", 2); self.assertEqual(rs.clear(), 2); self.assertEqual(len(rs), 0)
    def test_len(self): rs = RateStop(10); rs.set("a", 1); rs.set("b", 2); self.assertEqual(len(rs), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RateStop(0)
    def test_deterministic(self): rs = RateStop(10); rs.set("a", 1); self.assertEqual(rs.get("a"), rs.get("a"))
    def test_many(self): rs = RateStop(10); [rs.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(rs), 5)
