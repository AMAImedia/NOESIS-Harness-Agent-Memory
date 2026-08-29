import time, unittest
from noesis_harness.rate_core import RateCore

class TestRateCore(unittest.TestCase):
    def test_core(self): rc = RateCore(10); self.assertEqual(rc.core("a", 1), 1)
    def test_cached(self): rc = RateCore(10); rc.core("a", 1); self.assertEqual(rc.core("a", 2), 1)
    def test_get(self): rc = RateCore(10); rc.set("a", 1); self.assertEqual(rc.get("a"), 1)
    def test_get_default(self): self.assertEqual(RateCore(10).get("x", 5), 5)
    def test_ttl(self): rc = RateCore(0.01); rc.set("a", 1); time.sleep(0.02); self.assertIsNone(rc.get("a"))
    def test_invalidate(self): rc = RateCore(10); rc.set("a", 1); self.assertTrue(rc.invalidate("a")); self.assertFalse(rc.invalidate("a"))
    def test_clear(self): rc = RateCore(10); rc.set("a", 1); rc.set("b", 2); self.assertEqual(rc.clear(), 2); self.assertEqual(len(rc), 0)
    def test_len(self): rc = RateCore(10); rc.set("a", 1); rc.set("b", 2); self.assertEqual(len(rc), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RateCore(0)
    def test_deterministic(self): rc = RateCore(10); rc.set("a", 1); self.assertEqual(rc.get("a"), rc.get("a"))
    def test_many(self): rc = RateCore(10); [rc.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(rc), 5)
