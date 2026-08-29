import unittest
from noesis_harness.stream_window import window_sum, window_avg

class TestStreamWindow(unittest.TestCase):
    def test_sum(self): self.assertEqual(list(window_sum([1,2,3,4,5], 3)), [6, 9, 12])
    def test_avg(self): self.assertEqual(list(window_avg([1,2,3,4,5], 3)), [2.0, 3.0, 4.0])
    def test_empty(self): self.assertEqual(list(window_sum([], 3)), [])
    def test_short(self): self.assertEqual(list(window_sum([1,2], 3)), [])
    def test_exact(self): self.assertEqual(list(window_sum([1,2,3], 3)), [6.0])
    def test_deterministic(self): self.assertEqual(list(window_sum([1,2,3], 2)), list(window_sum([1,2,3], 2)))
    def test_many(self): self.assertEqual(len(list(window_sum(range(10), 3))), 8)
    def test_single(self): self.assertEqual(list(window_sum([5], 3)), [])
    def test_size_one(self): self.assertEqual(list(window_sum([1,2,3], 1)), [1.0, 2.0, 3.0])
    def test_no_crash(self): list(window_sum([], 5))
