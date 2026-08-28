import unittest
from noesis_harness.semaphore import Semaphore

class TestSemaphore(unittest.TestCase):
    def test_acquire(self): s = Semaphore(1); self.assertTrue(s.acquire()); self.assertEqual(int(s), 0)
    def test_release(self): s = Semaphore(1); s.acquire(); s.release(); self.assertEqual(int(s), 1)
    def test_block(self): s = Semaphore(0); self.assertFalse(s.acquire())
    def test_invalid(self):
        with self.assertRaises(ValueError): Semaphore(-1)
    def test_multiple(self): s = Semaphore(3); self.assertTrue(s.acquire()); self.assertTrue(s.acquire()); self.assertTrue(s.acquire()); self.assertFalse(s.acquire()); self.assertEqual(int(s), 0)
    def test_release_no_acquire(self): s = Semaphore(0); s.release(); self.assertEqual(int(s), 1)
    def test_determinism(self): a = Semaphore(2); b = Semaphore(2); a.acquire(); b.acquire(); self.assertEqual(int(a), int(b))
    def test_full(self): self.assertEqual(int(Semaphore(5)), 5)
    def test_repeated(self):
        s = Semaphore(1)
        for _ in range(3): s.acquire(); s.release()
        self.assertEqual(int(s), 1)
    def test_int(self): self.assertEqual(int(Semaphore(4)), 4)
