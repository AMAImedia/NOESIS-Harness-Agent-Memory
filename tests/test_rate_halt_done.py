import time, unittest
from noesis_harness.rate_halt_done import RateHaltDone

class TestRateHaltDone(unittest.TestCase):
    def test_halt_done(self): rh = RateHaltDone(10); self.assertEqual(rh.halt_done("a", 1), 1)
    def test_cached(self): rh = RateHaltDone(10); rh.halt_done("a", 1); self.assertEqual(rh.halt_done("a", 2), 1)
    def test_get(self): rh = RateHaltDone(10); rh.set("a", 1); self.assertEqual(rh.get("a"), 1)
    def test_get_default(self): self.assertEqual(RateHaltDone(10).get("x", 5), 5)
    def test_ttl(self): rh = RateHaltDone(0.01); rh.set("a", 1); time.sleep(0.02); self.assertIsNone(rh.get("a"))
    def test_invalidate(self): rh = RateHaltDone(10); rh.set("a", 1); self.assertTrue(rh.invalidate("a")); self.assertFalse(rh.invalidate("a"))
    def test_clear(self): rh = RateHaltDone(10); rh.set("a", 1); rh.set("b", 2); self.assertEqual(rh.clear(), 2); self.assertEqual(len(rh), 0)
    def test_len(self): rh = RateHaltDone(10); rh.set("a", 1); rh.set("b", 2); self.assertEqual(len(rh), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RateHaltDone(0)
    def test_deterministic(self): rh = RateHaltDone(10); rh.set("a", 1); self.assertEqual(rh.get("a"), rh.get("a"))
    def test_many(self): rh = RateHaltDone(10); [rh.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(rh), 5)
