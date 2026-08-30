import unittest
from noesis_harness.trajectory_analyzer import TrajectoryAnalyzer

class TestTrajectoryAnalyzer(unittest.TestCase):
    def test_record(self):
        t = TrajectoryAnalyzer(); t.record({"steps": 5}, "success"); self.assertEqual(t.success_rate(), 1.0)
    def test_diff(self):
        t = TrajectoryAnalyzer()
        t.record({"steps": 5, "quality": 0.9, "actions": ["a", "b"]}, "success")
        t.record({"steps": 10, "quality": 0.3, "actions": ["a", "c"]}, "failure")
        d = t.diff(); self.assertEqual(d["status"], "ok"); self.assertIn("a", d["action_differential"])
    def test_insufficient(self):
        t = TrajectoryAnalyzer(); t.record({}, "success"); self.assertEqual(t.diff()["status"], "insufficient_data")
    def test_recommended(self):
        t = TrajectoryAnalyzer()
        for _ in range(5): t.record({"actions": ["x", "y"]}, "success")
        for _ in range(5): t.record({"actions": ["y", "z"]}, "failure")
        d = t.diff(); self.assertEqual(d["recommended"][0][0], "x")
    def test_avg(self):
        t = TrajectoryAnalyzer()
        t.record({"steps": 10}, "success"); t.record({"steps": 20}, "success")
        self.assertEqual(t._avg(t._success, "steps"), 15.0)
    def test_deterministic(self):
        a = TrajectoryAnalyzer(); b = TrajectoryAnalyzer()
        for _ in range(5): a.record({"actions": ["x"]}, "success"); b.record({"actions": ["x"]}, "success")
        for _ in range(5): a.record({"actions": ["y"]}, "failure"); b.record({"actions": ["y"]}, "failure")
        self.assertEqual(a.diff(), b.diff())
    def test_many(self):
        t = TrajectoryAnalyzer()
        for i in range(100): t.record({"steps": i, "quality": i/100, "actions": ["a"]}, "success" if i % 2 == 0 else "failure")
        self.assertEqual(t.success_rate(), 0.5)
