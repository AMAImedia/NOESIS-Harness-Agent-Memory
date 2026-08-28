import unittest
from noesis_harness.stats import mean, median, variance, stdev

class TestStats(unittest.TestCase):
    def test_mean(self): self.assertEqual(mean([1, 2, 3]), 2.0)
    def test_mean_empty(self): self.assertEqual(mean([]), 0.0)
    def test_median_odd(self): self.assertEqual(median([3, 1, 2]), 2)
    def test_median_even(self): self.assertEqual(median([1, 2, 3, 4]), 2.5)
    def test_median_empty(self): self.assertEqual(median([]), 0.0)
    def test_variance(self): self.assertAlmostEqual(variance([2, 4]), 2.0)
    def test_variance_one(self): self.assertEqual(variance([5]), 0.0)
    def test_stdev(self): self.assertAlmostEqual(stdev([2, 4]), 2 ** 0.5)
    def test_determinism(self): self.assertEqual(mean([1, 2, 3]), mean([3, 2, 1]))
    def test_negative(self): self.assertEqual(mean([-1, 1]), 0.0)
