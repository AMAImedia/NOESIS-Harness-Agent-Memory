import time, unittest
from noesis_harness.rate_quit import RateQuit

class TestRateQuit(unittest.TestCase):
    def test_quit(self): rq = RateQuit(10); self.assertEqual(rq.quit("a", 1), 1)
    def test_cached(self): rq = RateQuit(10); rq.quit("a", 1); self.assertEqual(rq.quit("a", 2), 1)
    def test_get(self): rq = RateQuit(10); rq.set("a", 1); self.assertEqual(rq.get("a"), 1)
    def test_get_default(self): self.assertEqual(RateQuit(10).get("x", 5), 5)
    def test_ttl(self): rq = RateQuit(0.01); rq.set("a", 1); time.sleep(0.02); self.assertIsNone(rq.get("a"))
    def test_invalidate(self): rq = RateQuit(10); rq.set("a", 1); self.assertTrue(rq.invalidate("a")); self.assertFalse(rq.invalidate("a"))
    def test_clear(self): rq = RateQuit(10); rq.set("a", 1); rq.set("b", 2); self.assertEqual(rq.clear(), 2); self.assertEqual(len(rq), 0)
    def test_len(self): rq = RateQuit(10); rq.set("a", 1); rq.set("b", 2); self.assertEqual(len(rq), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RateQuit(0)
    def test_deterministic(self): rq = RateQuit(10); rq.set("a", 1); self.assertEqual(rq.get("a"), rq.get("a"))
    def test_many(self): rq = RateQuit(10); [rq.set(f"k{i}", i) for i in range(5)]; self.assertEqual(len(rq), 5)
