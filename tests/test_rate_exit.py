import time, unittest
from noesis_harness.rate_exit import RateExit

class TestRateExit(unittest.TestCase):
    def test_exit(self): re = RateExit(10); self.assertEqual(re.exit("a", 1), 1)
    def test_cached(self): re = RateExit(10); re.exit("a", 1); self.assertEqual(re.exit("a", 2), 1)
    def test_get(self): re = RateExit(10); re.set("a", 1); self.assertEqual(re.get("a"), 1)
    def test_get_default(self): self.assertEqual(RateExit(10).get("x", 5), 5)
    def test_ttl(self): re = RateExit(0.01); re.set("a", 1); time.sleep(0.02); self.assertIsNone(re.get("a"))
    def test_invalidate(self): re = RateExit(10); re.set("a", 1); self.assertTrue(re.invalidate("a")); self.assertFalse(re.invalidate("a"))
    def test_clear(self): re = RateExit(10); re.set("a", 1); re.set("b", 2); self.assertEqual(re.clear(), 2); self.assertEqual(len(re), 0)
    def test_len(self): re = RateExit(10); re.set("a", 1); re.set("b", 2); self.assertEqual(len(re), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RateExit(0)
    def test_deterministic(self): re = RateExit(10); re.set("a", 1); self.assertEqual(re.get("a"), re.get("a"))
    def test_many(self): re = RateExit(10); [re.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(re), 5)
