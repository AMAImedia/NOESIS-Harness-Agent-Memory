import unittest
from noesis_harness.pool import Pool

class TestPool(unittest.TestCase):
    def test_acquire(self): p = Pool(lambda: object(), 2); self.assertIsNotNone(p.acquire())
    def test_release(self): p = Pool(lambda: 1, 2); p.release(1); self.assertEqual(len(p), 1)
    def test_reuse(self): p = Pool(lambda: 99, 2); p.release(7); self.assertEqual(p.acquire(), 7)
    def test_invalid(self):
        with self.assertRaises(ValueError): Pool(lambda: None, 0)
    def test_max(self): p = Pool(lambda: 1, 2); p.release(1); p.release(2); p.release(3); self.assertEqual(len(p), 2)
    def test_factory_differs(self): p = Pool(lambda: object(), 5); a = p.acquire(); b = p.acquire(); self.assertNotEqual(id(a), id(b))
    def test_determinism(self):
        a = Pool(lambda: 1, 2); b = Pool(lambda: 1, 2); a.release(1); b.release(1); self.assertEqual(len(a), len(b))
    def test_many(self):
        p = Pool(lambda: 1, 5)
        for _ in range(3): p.release(1)
        self.assertEqual(len(p), 3)
    def test_empty_len(self): self.assertEqual(len(Pool(lambda: 1, 3)), 0)
    def test_acquire_after_release(self): p = Pool(lambda: "new", 2); p.release("old"); self.assertEqual(p.acquire(), "old")
