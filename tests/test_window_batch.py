import unittest
from noesis_harness.window_batch import window_batch, sliding_windows

class TestWindowBatch(unittest.TestCase):
    def test_batch(self): self.assertEqual(list(window_batch(iter([1,2,3,4,5]), 3)), [[1,2,3],[2,3,4],[3,4,5]])
    def test_sliding(self): self.assertEqual(sliding_windows([1,2,3,4,5], 3), [[1,2,3],[2,3,4],[3,4,5]])
    def test_empty(self): self.assertEqual(list(window_batch(iter([]), 3)), [])
    def test_sliding_empty(self): self.assertEqual(sliding_windows([], 3), [])
    def test_short(self): self.assertEqual(list(window_batch(iter([1,2]), 3)), [])
    def test_sliding_short(self): self.assertEqual(sliding_windows([1,2], 3), [])
    def test_exact(self): self.assertEqual(list(window_batch(iter([1,2,3]), 3)), [[1,2,3]])
    def test_sliding_exact(self): self.assertEqual(sliding_windows([1,2,3], 3), [[1,2,3]])
    def test_deterministic(self): self.assertEqual(list(window_batch(iter([1,2,3]), 2)), list(window_batch(iter([1,2,3]), 2)))
    def test_many(self): self.assertEqual(len(list(window_batch(iter(range(10)), 3))), 8)
    def test_no_crash(self): list(window_batch(iter([]), 5))
