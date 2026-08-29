import unittest
from noesis_harness.async_dedup import parallel_dedup

class TestAsyncDedup(unittest.TestCase):
    def test_basic(self): self.assertEqual(parallel_dedup(lambda x: x, [1, 2, 1, 3, 2]), [1, 2, 3])
    def test_empty(self): self.assertEqual(parallel_dedup(lambda x: x, []), [])
    def test_single(self): self.assertEqual(parallel_dedup(lambda x: x, [5]), [5])
    def test_all_same(self): self.assertEqual(parallel_dedup(lambda x: x, [1, 1, 1]), [1])
    def test_deterministic(self): self.assertEqual(parallel_dedup(lambda x: x, [1, 2, 1]), [1, 2])
    def test_many(self): self.assertEqual(parallel_dedup(lambda x: x, list(range(10))), list(range(10)))
    def test_workers(self): self.assertEqual(parallel_dedup(lambda x: x, [1, 2, 3], max_workers=1), [1, 2, 3])
    def test_no_crash(self): parallel_dedup(lambda x: x, [])
    def test_transform(self): self.assertEqual(parallel_dedup(lambda x: x * 2, [1, 2, 3, 4]), [2, 4, 6, 8])
    def test_partial_dedup(self): self.assertEqual(parallel_dedup(lambda x: x % 3, [1, 2, 3, 4, 5]), [1, 2, 0])
