import unittest
from noesis_harness.timer import Timer

class TestTimer(unittest.TestCase):
    def test_elapsed(self): t = Timer(start=0); self.assertAlmostEqual(t.elapsed(now=5), 5)
    def test_zero(self): t = Timer(start=10); self.assertAlmostEqual(t.elapsed(now=10), 0)
    def test_negative_clamped(self): t = Timer(start=10); self.assertEqual(t.elapsed(now=5), 0.0)
    def test_reset(self): t = Timer(start=0); t.reset(now=10); self.assertAlmostEqual(t.elapsed(now=15), 5)
    def test_determinism(self): a = Timer(start=0); b = Timer(start=0); self.assertEqual(a.elapsed(now=5), b.elapsed(now=5))
    def test_default_start(self): t = Timer(); self.assertGreaterEqual(t.elapsed(), 0)
    def test_many(self):
        t = Timer(start=0)
        for i in range(10): self.assertAlmostEqual(t.elapsed(now=i), float(i))
    def test_reset_default(self): t = Timer(start=0); t.reset(); self.assertGreaterEqual(t.elapsed(), 0)
    def test_initial(self): t = Timer(start=5); self.assertEqual(t.start, 5)
    def test_elapsed_float(self): t = Timer(start=0.5); self.assertAlmostEqual(t.elapsed(now=1.5), 1.0)
