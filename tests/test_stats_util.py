import unittest
from noesis_harness.stats_util import percentile, zscore, moving_avg

class TestStatsUtil(unittest.TestCase):
    def test_percentile_50(self): self.assertEqual(percentile([1, 2, 3, 4, 5], 0.5), 3.0)
    def test_percentile_0(self): self.assertEqual(percentile([1, 2, 3], 0.0), 1.0)
    def test_percentile_100(self): self.assertEqual(percentile([1, 2, 3], 1.0), 3.0)
    def test_percentile_empty(self): self.assertEqual(percentile([], 0.5), 0.0)
    def test_zscore(self): self.assertAlmostEqual(zscore(5, [1, 2, 3, 4, 5]), 1.2649, places=2)
    def test_zscore_empty(self): self.assertEqual(zscore(5, []), 0.0)
    def test_zscore_single(self): self.assertEqual(zscore(5, [5]), 0.0)
    def test_moving_avg(self): self.assertEqual(moving_avg([1, 2, 3, 4], 2), [1.0, 1.5, 2.5, 3.5])
    def test_moving_avg_invalid(self):
        with self.assertRaises(ValueError): moving_avg([1], 0)
    def test_deterministic(self): self.assertEqual(percentile([1, 2, 3], 0.5), percentile([1, 2, 3], 0.5))
