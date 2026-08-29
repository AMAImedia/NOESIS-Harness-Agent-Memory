import time, unittest
from noesis_harness.progress_util import ProgressTracker

class TestProgressUtil(unittest.TestCase):
    def test_tick(self): p = ProgressTracker(10); p.tick(); self.assertEqual(p.done(), 0.1)
    def test_finished(self): p = ProgressTracker(2); p.tick(); p.tick(); self.assertTrue(p.finished())
    def test_not_finished(self): p = ProgressTracker(3); p.tick(); self.assertFalse(p.finished())
    def test_elapsed(self): p = ProgressTracker(1); p.tick(); self.assertGreater(p.elapsed(), 0)
    def test_eta(self): p = ProgressTracker(10); p.tick(); self.assertGreater(p.eta(), 0)
    def test_invalid(self):
        with self.assertRaises(ValueError): ProgressTracker(0)
    def test_done(self): p = ProgressTracker(1); p.tick(); self.assertEqual(p.done(), 1.0)
    def test_len(self): p = ProgressTracker(3); p.tick(); p.tick(); self.assertEqual(len(p), 2)
    def test_deterministic(self): p = ProgressTracker(1); p.tick(); self.assertEqual(p.done(), 1.0)
    def test_many(self): p = ProgressTracker(100); [p.tick() for _ in range(100)]; self.assertTrue(p.finished())
