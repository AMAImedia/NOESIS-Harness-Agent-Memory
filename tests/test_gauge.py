import unittest
from noesis_harness.gauge import Gauge

class TestGauge(unittest.TestCase):
    def test_set_get(self): g = Gauge(); g.set(5); self.assertEqual(g.get(), 5)
    def test_inc(self): g = Gauge(1); self.assertAlmostEqual(g.inc(2), 3)
    def test_dec(self): g = Gauge(5); self.assertAlmostEqual(g.dec(1), 4)
    def test_initial(self): self.assertEqual(Gauge(2.5).get(), 2.5)
    def test_negative(self): g = Gauge(); g.set(-1); self.assertEqual(g.get(), -1)
    def test_float(self): g = Gauge(0.5); g.inc(0.5); self.assertAlmostEqual(g.get(), 1.0)
    def test_overwrite(self): g = Gauge(1); g.set(2); g.set(3); self.assertEqual(g.get(), 3)
    def test_determinism(self): a = Gauge(1); b = Gauge(1); a.inc(1); b.inc(1); self.assertEqual(a.get(), b.get())
    def test_zero(self): g = Gauge(); self.assertEqual(g.get(), 0)
    def test_inc_dec(self): g = Gauge(10); g.inc(5); g.dec(3); self.assertAlmostEqual(g.get(), 12)
