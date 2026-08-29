import time, unittest
from noesis_harness.rate_done import RateDone

class TestRateDone(unittest.TestCase):
    def test_done(self): rd = RateDone(10); self.assertEqual(rd.done("a", 1), 1)
    def test_cached(self): rd = RateDone(10); rd.done("a", 1); self.assertEqual(rd.done("a", 2), 1)
    def test_get(self): rd = RateDone(10); rd.set("a", 1); self.assertEqual(rd.get("a"), 1)
    def test_get_default(self): self.assertEqual(RateDone(10).get("x", 5), 5)
    def test_ttl(self): rd = RateDone(0.01); rd.set("a", 1); time.sleep(0.02); self.assertIsNone(rd.get("a"))
    def test_invalidate(self): rd = RateDone(10); rd.set("a", 1); self.assertTrue(rd.invalidate("a")); self.assertFalse(rd.invalidate("a"))
    def test_clear(self): rd = RateDone(10); rd.set("a", 1); rd.set("b", 2); self.assertEqual(rd.clear(), 2); self.assertEqual(len(rd), 0)
    def test_len(self): rd = RateDone(10); rd.set("a", 1); rd.set("b", 2); self.assertEqual(len(rd), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RateDone(0)
    def test_deterministic(self): rd = RateDone(10); rd.set("a", 1); self.assertEqual(rd.get("a"), rd.get("a"))
    def test_many(self): rd = RateDone(10); [rd.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(rd), 5)
