import unittest
from noesis_harness.async_parallel import parallel_run, parallel_map, parallel_filter

class TestAsyncParallel(unittest.TestCase):
    def test_run(self): self.assertEqual(parallel_run([lambda: 1, lambda: 2]), [1, 2])
    def test_map(self): self.assertEqual(parallel_map(lambda x: x * 2, [1, 2, 3]), [2, 4, 6])
    def test_filter(self): self.assertEqual(parallel_filter(lambda x: x > 2, [1, 2, 3, 4]), [3, 4])
    def test_empty(self): self.assertEqual(parallel_run([]), [])
    def test_map_empty(self): self.assertEqual(parallel_map(lambda x: x, []), [])
    def test_filter_empty(self): self.assertEqual(parallel_filter(lambda x: True, []), [])
    def test_deterministic(self): self.assertEqual(parallel_run([lambda: 5]), [5])
    def test_many(self): self.assertEqual(parallel_map(lambda x: x + 1, range(10)), list(range(1, 11)))
    def test_workers(self): self.assertEqual(parallel_map(lambda x: x, [1, 2, 3], max_workers=1), [1, 2, 3])
    def test_no_crash(self): parallel_run([lambda: None, lambda: None])
