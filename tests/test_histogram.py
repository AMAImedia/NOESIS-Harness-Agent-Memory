import unittest
from noesis_harness.histogram import Histogram

class TestHist(unittest.TestCase):
    def test_observe(self): h = Histogram([1, 5, 10]); h.observe(0); h.observe(3); h.observe(6); h.observe(11); self.assertEqual(h.to_dict()["counts"], [1, 1, 1, 1])
    def test_total(self): h = Histogram([5]); h.observe(1); h.observe(10); self.assertEqual(h.total, 2)
    def test_empty(self): h = Histogram([1]); self.assertEqual(h.to_dict()["total"], 0)
    def test_boundary(self): h = Histogram([5]); h.observe(5); self.assertEqual(h.counts[0], 1)
    def test_overflow(self): h = Histogram([1]); h.observe(2); self.assertEqual(h.counts[1], 1)
    def test_determinism(self):
        a = Histogram([1, 5]); b = Histogram([1, 5])
        for v in [0, 3, 6]: a.observe(v); b.observe(v)
        self.assertEqual(a.to_dict(), b.to_dict())
    def test_sorted_buckets(self): h = Histogram([10, 1, 5]); self.assertEqual(h.buckets, [1, 5, 10])
    def test_to_dict(self): h = Histogram([1]); h.observe(0); d = h.to_dict(); self.assertIn("buckets", d); self.assertIn("counts", d)
    def test_many(self):
        h = Histogram([5, 10])
        for i in range(100): h.observe(i % 12)
        self.assertEqual(h.total, 100)
    def test_negative(self): h = Histogram([0]); h.observe(-1); self.assertEqual(h.counts[0], 1)
