import unittest
from noesis_harness.hist_linear import LinearHist

class TestLinearHist(unittest.TestCase):
    def test_record(self): h = LinearHist(0, 10, 5); h.record(1); self.assertEqual(h.counts()[0], 1)
    def test_bins(self): h = LinearHist(0, 10, 5); [h.record(i) for i in range(10)]; self.assertEqual(len(h.counts()), 5)
    def test_total(self): h = LinearHist(0, 10, 5); [h.record(i) for i in range(10)]; self.assertEqual(h.total(), 10)
    def test_clamp_high(self): h = LinearHist(0, 10, 5); h.record(999); self.assertEqual(h.counts()[-1], 1)
    def test_clamp_low(self): h = LinearHist(0, 10, 5); h.record(-1); self.assertEqual(h.counts()[0], 1)
    def test_invalid_bins(self):
        with self.assertRaises(ValueError): LinearHist(0, 10, 0)
    def test_invalid_range(self):
        with self.assertRaises(ValueError): LinearHist(10, 0, 5)
    def test_mid(self): h = LinearHist(0, 10, 10); h.record(5); self.assertEqual(h.counts()[5], 1)
    def test_determinism(self): a = LinearHist(0, 10, 4); b = LinearHist(0, 10, 4); a.record(3); b.record(3); self.assertEqual(a.counts(), b.counts())
    def test_empty(self): self.assertEqual(LinearHist(0, 10, 3).total(), 0)
    def test_boundary(self): h = LinearHist(0, 10, 10); h.record(10); self.assertEqual(h.counts()[-1], 1)
