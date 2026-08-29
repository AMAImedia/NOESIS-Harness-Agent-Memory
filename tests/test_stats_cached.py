import unittest
from noesis_harness.stats_cached import RunningStats

class TestRunningStats(unittest.TestCase):
    def test_empty(self): rs = RunningStats(); self.assertEqual(rs.count(), 0); self.assertEqual(rs.mean(), 0.0)
    def test_one(self): rs = RunningStats(); rs.update(5); self.assertEqual(rs.mean(), 5.0)
    def test_two(self): rs = RunningStats(); rs.update(2); rs.update(4); self.assertEqual(rs.mean(), 3.0)
    def test_variance(self):
        rs = RunningStats()
        for x in [2, 4, 4, 4, 5, 5, 7, 9]: rs.update(x)
        self.assertAlmostEqual(rs.mean(), 5.0)
        self.assertAlmostEqual(rs.variance(), 4.5714, places=2)
    def test_stdev(self):
        rs = RunningStats()
        for x in [2, 4, 4, 4, 5, 5, 7, 9]: rs.update(x)
        self.assertAlmostEqual(rs.stdev(), 2.138, places=2)
    def test_count(self): rs = RunningStats(); [rs.update(i) for i in range(10)]; self.assertEqual(rs.count(), 10)
    def test_deterministic(self): rs = RunningStats(); rs.update(5); self.assertEqual(rs.mean(), rs.mean())
    def test_many(self):
        rs = RunningStats()
        for i in range(100): rs.update(float(i))
        self.assertEqual(rs.count(), 100)
        self.assertAlmostEqual(rs.mean(), 49.5)
    def test_no_mutation(self): rs = RunningStats(); rs.update(1); rs.mean(); self.assertEqual(rs.count(), 1)
    def test_single_variance(self): rs = RunningStats(); rs.update(5); self.assertEqual(rs.variance(), 0.0)
