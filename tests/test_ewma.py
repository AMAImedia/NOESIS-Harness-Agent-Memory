import unittest
from noesis_harness.ewma import EWMA

class TestEWMA(unittest.TestCase):
    def test_first(self): self.assertEqual(EWMA(0.5).update(10), 10)
    def test_smooth(self):
        e = EWMA(0.5); e.update(0); v = e.update(10); self.assertAlmostEqual(v, 5.0)
    def test_invalid(self):
        with self.assertRaises(ValueError): EWMA(0)
    def test_count(self): e = EWMA(0.5); e.update(1); e.update(2); self.assertEqual(e.count(), 2)
    def test_value(self): e = EWMA(0.5); e.update(4); self.assertEqual(e.value(), 4)
    def test_converge(self):
        e = EWMA(0.1)
        for _ in range(50): e.update(100)
        self.assertAlmostEqual(e.value(), 100.0, delta=1e-6)
    def test_stays(self):
        e = EWMA(0.5); e.update(2); e.update(2); self.assertEqual(e.value(), 2)
    def test_determinism(self):
        a = EWMA(0.3); b = EWMA(0.3); a.update(5); b.update(5); self.assertEqual(a.value(), b.value())
    def test_alpha_one(self):
        e = EWMA(1.0); self.assertEqual(e.update(3), 3)
    def test_no_value(self): self.assertIsNone(EWMA(0.5).value())
