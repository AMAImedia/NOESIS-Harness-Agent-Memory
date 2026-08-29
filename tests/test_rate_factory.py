import time, unittest
from noesis_harness.rate_factory import RateFactory

class TestRateFactory(unittest.TestCase):
    def test_get(self): rf = RateFactory(10, lambda k: k * 2); self.assertEqual(rf.get("a"), "aa")
    def test_missing(self): self.assertIsNone(RateFactory(10).get("x"))
    def test_ttl(self): rf = RateFactory(0.01, lambda k: 1); rf.get("a"); time.sleep(0.02); self.assertEqual(rf.get("a"), 1)
    def test_invalidate(self): rf = RateFactory(10, lambda k: 1); rf.get("a"); self.assertTrue(rf.invalidate("a")); self.assertIsNone(rf.get("a"))
    def test_clear(self): rf = RateFactory(10, lambda k: 1); rf.get("a"); rf.get("b"); self.assertEqual(rf.clear(), 2); self.assertEqual(len(rf), 0)
    def test_len(self): rf = RateFactory(10, lambda k: k); rf.get("a"); rf.get("b"); self.assertEqual(len(rf), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RateFactory(0)
    def test_deterministic(self): rf = RateFactory(10, lambda k: 5); self.assertEqual(rf.get("a"), rf.get("a"))
    def test_many(self): rf = RateFactory(10, lambda k: k); [rf.get(f"k{i}") for i in range(5)]; self.assertEqual(len(rf), 5)
    def test_no_factory(self): self.assertIsNone(RateFactory(10).get("x"))
