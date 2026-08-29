import threading, unittest
from noesis_harness.bucket_parallel import BucketParallel

class TestBucketParallel(unittest.TestCase):
    def test_acquire(self): bp = BucketParallel(3); self.assertTrue(bp.acquire())
    def test_full(self): bp = BucketParallel(2); bp.acquire(); bp.acquire(); self.assertFalse(bp.acquire())
    def test_release(self): bp = BucketParallel(2); bp.acquire(); bp.release(); self.assertTrue(bp.acquire())
    def test_tokens(self): bp = BucketParallel(3); bp.acquire(); bp.acquire(); self.assertEqual(bp.tokens(), 2)
    def test_free(self): bp = BucketParallel(3); bp.acquire(); self.assertEqual(bp.free(), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): BucketParallel(0)
    def test_len(self): bp = BucketParallel(3); bp.acquire(); bp.acquire(); self.assertEqual(len(bp), 2)
    def test_thread_safe(self):
        bp = BucketParallel(100); acquired = [0]
        def worker():
            for _ in range(50):
                if bp.acquire(): acquired[0] += 1
        threads = [threading.Thread(target=worker) for _ in range(3)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(acquired[0], 100)
    def test_many(self): bp = BucketParallel(5); [bp.acquire() for _ in range(5)]; self.assertFalse(bp.acquire())
    def test_no_crash(self): bp = BucketParallel(1); bp.acquire(); bp.release(); bp.acquire()
