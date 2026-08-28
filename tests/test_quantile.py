import unittest
from noesis_harness.quantile import quantile

class TestQuantile(unittest.TestCase):
    def test_median(self): self.assertAlmostEqual(quantile([1, 2, 3, 4], 0.5), 2.5)
    def test_min(self): self.assertEqual(quantile([1, 2, 3, 4], 0.0), 1)
    def test_max(self): self.assertEqual(quantile([1, 2, 3, 4], 1.0), 4)
    def test_empty(self): self.assertEqual(quantile([], 0.5), 0.0)
    def test_single(self): self.assertEqual(quantile([7], 0.3), 7)
    def test_invalid(self):
        with self.assertRaises(ValueError): quantile([1], 2)
    def test_quarter(self): self.assertAlmostEqual(quantile([1, 2, 3, 4, 5], 0.25), 2.0)
    def test_determinism(self): self.assertEqual(quantile([5, 1, 3], 0.5), quantile([1, 3, 5], 0.5))
    def test_order(self): xs = list(range(1, 11)); self.assertLess(quantile(xs, 0.25), quantile(xs, 0.75))
    def test_interp(self): self.assertAlmostEqual(quantile([10, 20], 0.5), 15.0)
