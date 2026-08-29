import time, unittest
from noesis_harness.rate_computed import RateComputed

class TestRateComputed(unittest.TestCase):
    def test_get(self): rc = RateComputed(10, lambda k: k * 2); self.assertEqual(rc.get("a"), "a" * 2)
    def test_missing(self): self.assertIsNone(RateComputed(10).get("x"))
    def test_ttl(self): rc = RateComputed(0.01, lambda k: 1); rc.get("a"); time.sleep(0.02); self.assertEqual(rc.get("a"), 1)
    def test_invalidate(self): rc = RateComputed(10, lambda k: 1); rc.get("a"); self.assertTrue(rc.invalidate("a")); self.assertFalse(rc.invalidate("a"))
    def test_clear(self): rc = RateComputed(10, lambda k: 1); rc.get("a"); rc.get("b"); self.assertEqual(rc.clear(), 2); self.assertEqual(len(rc), 0)
    def test_len(self): rc = RateComputed(10, lambda k: k); rc.get("a"); rc.get("b"); self.assertEqual(len(rc), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RateComputed(0)
    def test_deterministic(self): rc = RateComputed(10, lambda k: 5); self.assertEqual(rc.get("a"), rc.get("a"))
    def test_many(self): rc = RateComputed(10, lambda k: k); [rc.get(f"k{i}") for i in range(5)]; self.assertEqual(len(rc), 5)
    def test_no_compute(self): self.assertIsNone(RateComputed(10).get("x"))
