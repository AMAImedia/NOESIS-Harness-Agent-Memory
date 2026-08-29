import unittest
from noesis_harness.progress_bar import Progress

class TestProgress(unittest.TestCase):
    def test_tick(self): p = Progress(10); p.tick(); self.assertEqual(p.done(), 0.1)
    def test_finished(self): p = Progress(2); p.tick(); p.tick(); self.assertTrue(p.finished())
    def test_not_finished(self): p = Progress(3); p.tick(); self.assertFalse(p.finished())
    def test_remaining(self): p = Progress(5); p.tick(); p.tick(); self.assertEqual(p.remaining(), 3)
    def test_invalid(self):
        with self.assertRaises(ValueError): Progress(0)
    def test_done(self): p = Progress(1); p.tick(); self.assertEqual(p.done(), 1.0)
    def test_len(self): p = Progress(3); p.tick(); p.tick(); self.assertEqual(len(p), 2)
    def test_deterministic(self): p = Progress(1); p.tick(); self.assertEqual(p.done(), 1.0)
    def test_many(self): p = Progress(100); [p.tick() for _ in range(100)]; self.assertTrue(p.finished())
    def test_zero_start(self): p = Progress(5); self.assertEqual(p.done(), 0.0)
