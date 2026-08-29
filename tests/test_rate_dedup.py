import time, unittest
from noesis_harness.rate_dedup import RateDedup

class TestRateDedup(unittest.TestCase):
    def test_check(self): rd = RateDedup(10); self.assertTrue(rd.check("a"))
    def test_duplicate(self): rd = RateDedup(10); rd.check("a"); self.assertFalse(rd.check("a"))
    def test_different(self): rd = RateDedup(10); rd.check("a"); self.assertTrue(rd.check("b"))
    def test_refill(self): rd = RateDedup(0.01); rd.check("a"); time.sleep(0.02); self.assertTrue(rd.check("a"))
    def test_count(self): rd = RateDedup(10); rd.check("a"); rd.check("b"); self.assertEqual(rd.count(), 2)
    def test_clear(self): rd = RateDedup(10); rd.check("a"); rd.check("b"); self.assertEqual(rd.clear(), 2); self.assertEqual(len(rd), 0)
    def test_invalid(self):
        with self.assertRaises(ValueError): RateDedup(0)
    def test_len(self): rd = RateDedup(10); rd.check("a"); rd.check("b"); self.assertEqual(len(rd), 2)
    def test_deterministic(self): rd = RateDedup(10); rd.check("a"); self.assertFalse(rd.check("a"))
    def test_many(self): rd = RateDedup(10); [rd.check(f"k{i}") for i in range(5)]; self.assertEqual(len(rd), 5)
