import unittest
from noesis_harness.sliding_window import SlidingWindow

class TestSW(unittest.TestCase):
    def test_add(self): w = SlidingWindow(3); w.add(1); w.add(2); self.assertEqual(w.values(), [1, 2])
    def test_overflow(self): w = SlidingWindow(2); w.add(1); w.add(2); w.add(3); self.assertEqual(w.values(), [2, 3])
    def test_avg(self): w = SlidingWindow(3); w.add(2); w.add(4); self.assertAlmostEqual(w.avg(), 3)
    def test_empty_avg(self): self.assertEqual(SlidingWindow(3).avg(), 0.0)
    def test_len(self): w = SlidingWindow(5); w.add(1); self.assertEqual(len(w), 1)
    def test_size_one(self): w = SlidingWindow(1); w.add(1); w.add(2); self.assertEqual(w.values(), [2])
    def test_invalid(self):
        with self.assertRaises(ValueError): SlidingWindow(0)
    def test_determinism(self):
        a = SlidingWindow(3); b = SlidingWindow(3)
        for x in [1, 2, 3, 4]: a.add(x); b.add(x)
        self.assertEqual(a.values(), b.values())
    def test_many(self):
        w = SlidingWindow(3)
        for i in range(10): w.add(i)
        self.assertEqual(w.values(), [7, 8, 9])
    def test_avg_window(self): w = SlidingWindow(2); w.add(10); w.add(20); w.add(30); self.assertAlmostEqual(w.avg(), 25)
