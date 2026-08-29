import time, unittest
from noesis_harness.rate_emit import RateEmit

class TestRateEmit(unittest.TestCase):
    def test_emit(self): re = RateEmit(10); self.assertEqual(re.emit("a", 1), 1)
    def test_cached(self): re = RateEmit(10); re.emit("a", 1); self.assertEqual(re.emit("a", 2), 1)
    def test_get(self): re = RateEmit(10); re.set("a", 1); self.assertEqual(re.get("a"), 1)
    def test_get_default(self): self.assertEqual(RateEmit(10).get("x", 5), 5)
    def test_ttl(self): re = RateEmit(0.01); re.set("a", 1); time.sleep(0.02); self.assertIsNone(re.get("a"))
    def test_invalidate(self): re = RateEmit(10); re.set("a", 1); self.assertTrue(re.invalidate("a")); self.assertFalse(re.invalidate("a"))
    def test_clear(self): re = RateEmit(10); re.set("a", 1); re.set("b", 2); self.assertEqual(re.clear(), 2); self.assertEqual(len(re), 0)
    def test_len(self): re = RateEmit(10); re.set("a", 1); re.set("b", 2); self.assertEqual(len(re), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RateEmit(0)
    def test_deterministic(self): re = RateEmit(10); re.set("a", 1); self.assertEqual(re.get("a"), re.get("a"))
    def test_many(self): re = RateEmit(10); [re.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(re), 5)
