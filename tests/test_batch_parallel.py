import unittest
from noesis_harness.batch_parallel import parallel_batch

class TestBatchParallel(unittest.TestCase):
    def test_basic(self): self.assertEqual(parallel_batch(lambda x: x * 2, [1, 2, 3, 4], 2), [2, 4, 6, 8])
    def test_empty(self): self.assertEqual(parallel_batch(lambda x: x, [], 2), [])
    def test_single(self): self.assertEqual(parallel_batch(lambda x: x + 1, [5], 10), [6])
    def test_exact(self): self.assertEqual(parallel_batch(lambda x: x, [1, 2, 3], 3), [1, 2, 3])
    def test_deterministic(self): self.assertEqual(parallel_batch(lambda x: x, [1, 2], 1), [1, 2])
    def test_many(self): self.assertEqual(parallel_batch(lambda x: x + 1, list(range(100)), 10), list(range(1, 101)))
    def test_workers(self): self.assertEqual(parallel_batch(lambda x: x, [1, 2, 3], 1, max_workers=1), [1, 2, 3])
    def test_no_crash(self): parallel_batch(lambda x: x, [], 5)
    def test_remainder(self): self.assertEqual(parallel_batch(lambda x: x, [1, 2, 3, 4, 5], 2), [1, 2, 3, 4, 5])
    def test_large_batch(self): self.assertEqual(parallel_batch(lambda x: x, list(range(10)), 100), list(range(10)))
