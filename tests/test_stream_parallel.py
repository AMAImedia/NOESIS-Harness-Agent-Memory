import unittest
from noesis_harness.stream_parallel import parallel_stream

class TestStreamParallel(unittest.TestCase):
    def test_basic(self): self.assertEqual(parallel_stream(lambda x: x * 2, iter([1,2,3,4]), 2), [2,4,6,8])
    def test_empty(self): self.assertEqual(parallel_stream(lambda x: x, iter([]), 2), [])
    def test_single(self): self.assertEqual(parallel_stream(lambda x: x + 1, iter([5]), 10), [6])
    def test_deterministic(self): self.assertEqual(parallel_stream(lambda x: x, iter([1,2]), 1), [1,2])
    def test_many(self): self.assertEqual(parallel_stream(lambda x: x + 1, iter(range(100)), 10), list(range(1,101)))
    def test_workers(self): self.assertEqual(parallel_stream(lambda x: x, iter([1,2,3]), 1, max_workers=1), [1,2,3])
    def test_no_crash(self): parallel_stream(lambda x: x, iter([]), 5)
    def test_remainder(self): self.assertEqual(parallel_stream(lambda x: x, iter([1,2,3,4,5]), 2), [1,2,3,4,5])
    def test_large_batch(self): self.assertEqual(parallel_stream(lambda x: x, iter(range(10)), 100), list(range(10)))
    def test_order(self): self.assertEqual(parallel_stream(lambda x: x, iter([3,1,2]), 10), [3,1,2])
