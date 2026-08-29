import time, unittest
from noesis_harness.rate_parallel import RateParallel

class TestRateParallel(unittest.TestCase):
    def test_allow(self): rp = RateParallel(3); self.assertTrue(rp.allow())
    def test_limit(self): rp = RateParallel(2); rp.allow(); rp.allow(); self.assertFalse(rp.allow())
    def test_refill(self): rp = RateParallel(2, 0.01); rp.allow(); rp.allow(); self.assertFalse(rp.allow()); time.sleep(0.02); self.assertTrue(rp.allow())
    def test_count(self): rp = RateParallel(3); rp.allow(); rp.allow(); self.assertEqual(rp.count(), 2)
    def test_remaining(self): rp = RateParallel(3); rp.allow(); self.assertEqual(rp.remaining(), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RateParallel(0)
    def test_deterministic(self): rp = RateParallel(3); rp.allow(); self.assertEqual(rp.count(), 1)
    def test_many(self): rp = RateParallel(5); [rp.allow() for _ in range(5)]; self.assertFalse(rp.allow())
    def test_no_crash(self): rp = RateParallel(10); [rp.allow() for _ in range(20)]
    def test_thread_safe(self):
        import threading; rp = RateParallel(100)
        def worker():
            for _ in range(50): rp.allow()
        threads = [threading.Thread(target=worker) for _ in range(3)]
        for t in threads: t.start()
        for t in threads: t.join()
