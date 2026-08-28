import unittest
from noesis_harness.barrier import Barrier

class TestBarrier(unittest.TestCase):
    def test_wait(self): b = Barrier(2); self.assertFalse(b.wait()); self.assertTrue(b.wait())
    def test_reset(self): b = Barrier(2); b.wait(); b.wait(); self.assertFalse(b.wait())
    def test_count(self): b = Barrier(3); b.wait(); self.assertEqual(int(b), 1)
    def test_invalid(self):
        with self.assertRaises(ValueError): Barrier(0)
    def test_single(self): self.assertTrue(Barrier(1).wait())
    def test_determinism(self): a = Barrier(2); b = Barrier(2); a.wait(); b.wait(); self.assertEqual(int(a), int(b))
    def test_reuse(self):
        b = Barrier(2)
        for _ in range(3): b.wait(); b.wait()
        self.assertFalse(b.wait())
    def test_many(self): b = Barrier(5); [b.wait() for _ in range(4)]; self.assertTrue(b.wait()); self.assertFalse(b.wait())
    def test_full(self): self.assertEqual(int(Barrier(3)), 0)
    def test_partial(self): b = Barrier(4); b.wait(); b.wait(); self.assertEqual(int(b), 2)
