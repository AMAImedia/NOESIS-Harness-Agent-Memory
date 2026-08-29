import time, unittest
from noesis_harness.rate_end import RateEnd

class TestRateEnd(unittest.TestCase):
    def test_end(self): re = RateEnd(10); self.assertEqual(re.end("a", 1), 1)
    def test_cached(self): re = RateEnd(10); re.end("a", 1); self.assertEqual(re.end("a", 2), 1)
    def test_get(self): re = RateEnd(10); re.set("a", 1); self.assertEqual(re.get("a"), 1)
    def test_get_default(self): self.assertEqual(RateEnd(10).get("x", 5), 5)
    def test_ttl(self): re = RateEnd(0.01); re.set("a", 1); time.sleep(0.02); self.assertIsNone(re.get("a"))
    def test_invalidate(self): re = RateEnd(10); re.set("a", 1); self.assertTrue(re.invalidate("a")); self.assertFalse(re.invalidate("a"))
    def test_clear(self): re = RateEnd(10); re.set("a", 1); re.set("b", 2); self.assertEqual(re.clear(), 2); self.assertEqual(len(re), 0)
    def test_len(self): re = RateEnd(10); re.set("a", 1); re.set("b", 2); self.assertEqual(len(re), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RateEnd(0)
    def test_deterministic(self): re = RateEnd(10); re.set("a", 1); self.assertEqual(re.get("a"), re.get("a"))
    def test_many(self): re = RateEnd(10); [re.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(re), 5)
