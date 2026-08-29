import time, unittest
from noesis_harness.rate_recv import RateRecv

class TestRateRecv(unittest.TestCase):
    def test_recv(self): rr = RateRecv(10); self.assertEqual(rr.recv("a", 1), 1)
    def test_cached(self): rr = RateRecv(10); rr.recv("a", 1); self.assertEqual(rr.recv("a", 2), 1)
    def test_get(self): rr = RateRecv(10); rr.set("a", 1); self.assertEqual(rr.get("a"), 1)
    def test_get_default(self): self.assertEqual(RateRecv(10).get("x", 5), 5)
    def test_ttl(self): rr = RateRecv(0.01); rr.set("a", 1); time.sleep(0.02); self.assertIsNone(rr.get("a"))
    def test_invalidate(self): rr = RateRecv(10); rr.set("a", 1); self.assertTrue(rr.invalidate("a")); self.assertFalse(rr.invalidate("a"))
    def test_clear(self): rr = RateRecv(10); rr.set("a", 1); rr.set("b", 2); self.assertEqual(rr.clear(), 2); self.assertEqual(len(rr), 0)
    def test_len(self): rr = RateRecv(10); rr.set("a", 1); rr.set("b", 2); self.assertEqual(len(rr), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RateRecv(0)
    def test_deterministic(self): rr = RateRecv(10); rr.set("a", 1); self.assertEqual(rr.get("a"), rr.get("a"))
    def test_many(self): rr = RateRecv(10); [rr.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(rr), 5)
