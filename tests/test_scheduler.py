import unittest
from noesis_harness.scheduler import Scheduler

class TestScheduler(unittest.TestCase):
    def test_every(self): s = Scheduler(); self.assertEqual(s.every(1.0, lambda: None), 1)
    def test_len(self): s = Scheduler(); s.every(1.0, lambda: None); s.every(2.0, lambda: None); self.assertEqual(len(s), 2)
    def test_run_pending(self):
        calls = []
        s = Scheduler(); s.every(1.0, lambda: calls.append(1))
        s.run_pending(2.0); self.assertEqual(calls, [1])
    def test_not_pending(self):
        calls = []
        s = Scheduler(); s.every(5.0, lambda: calls.append(1))
        s.run_pending(2.0); self.assertEqual(calls, [])
    def test_invalid(self):
        with self.assertRaises(ValueError): Scheduler().every(0, lambda: None)
    def test_many(self):
        calls = []
        s = Scheduler()
        for _ in range(3): s.every(1.0, lambda: calls.append(1))
        s.run_pending(1.0); self.assertEqual(len(calls), 3)
    def test_determinism(self):
        a = Scheduler(); a.every(1.0, lambda: None); b = Scheduler(); b.every(1.0, lambda: None)
        self.assertEqual(len(a), len(b))
    def test_run_multiple(self):
        calls = []
        s = Scheduler(); s.every(1.0, lambda: calls.append(1)); s.every(1.0, lambda: calls.append(2))
        s.run_pending(1.0); self.assertEqual(calls, [1, 2])
    def test_empty(self): s = Scheduler(); s.run_pending(5.0)
    def test_clear(self): s = Scheduler(); s.every(1.0, lambda: None); self.assertEqual(len(s), 1)
