import time, unittest
from noesis_harness.rate_map import RateMap

class TestRateMap(unittest.TestCase):
    def test_mapping(self): rm = RateMap(10); self.assertEqual(rm.mapping("a", 1), 1)
    def test_cached(self): rm = RateMap(10); rm.mapping("a", 1); self.assertEqual(rm.mapping("a", 2), 1)
    def test_get(self): rm = RateMap(10); rm.set("a", 1); self.assertEqual(rm.get("a"), 1)
    def test_get_default(self): self.assertEqual(RateMap(10).get("x", 5), 5)
    def test_ttl(self): rm = RateMap(0.01); rm.set("a", 1); time.sleep(0.02); self.assertIsNone(rm.get("a"))
    def test_invalidate(self): rm = RateMap(10); rm.set("a", 1); self.assertTrue(rm.invalidate("a")); self.assertFalse(rm.invalidate("a"))
    def test_clear(self): rm = RateMap(10); rm.set("a", 1); rm.set("b", 2); self.assertEqual(rm.clear(), 2); self.assertEqual(len(rm), 0)
    def test_len(self): rm = RateMap(10); rm.set("a", 1); rm.set("b", 2); self.assertEqual(len(rm), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RateMap(0)
    def test_deterministic(self): rm = RateMap(10); rm.set("a", 1); self.assertEqual(rm.get("a"), rm.get("a"))
    def test_many(self): rm = RateMap(10); [rm.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(rm), 5)
