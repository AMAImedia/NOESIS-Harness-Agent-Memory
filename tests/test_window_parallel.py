import unittest
from noesis_harness.window_parallel import parallel_window

class TestWindowParallel(unittest.TestCase):
    def test_basic(self): self.assertEqual(parallel_window(sum, [1,2,3,4,5], 3), [6,9,12])
    def test_empty(self): self.assertEqual(parallel_window(sum, [], 3), [])
    def test_short(self): self.assertEqual(parallel_window(sum, [1,2], 3), [])
    def test_exact(self): self.assertEqual(parallel_window(sum, [1,2,3], 3), [6])
    def test_deterministic(self): self.assertEqual(parallel_window(sum, [1,2,3], 2), [3,5])
    def test_many(self): self.assertEqual(len(parallel_window(sum, list(range(10)), 3)), 8)
    def test_workers(self): self.assertEqual(parallel_window(sum, [1,2,3], 2, max_workers=1), [3,5])
    def test_no_crash(self): parallel_window(sum, [], 5)
    def test_size_one(self): self.assertEqual(parallel_window(sum, [1,2,3], 1), [1,2,3])
    def test_lambda(self): self.assertEqual(parallel_window(lambda w: max(w), [1,3,2,4,5], 3), [3,4,5])
