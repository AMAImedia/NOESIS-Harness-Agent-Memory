import unittest
from noesis_harness.async_util import run_sync, parallel_map

class TestAsyncUtil(unittest.TestCase):
    def test_run_sync(self): self.assertEqual(run_sync(lambda: 1 + 2), 3)
    def test_run_sync_args(self): self.assertEqual(run_sync(lambda x, y: x + y, 1, 2), 3)
    def test_parallel_map(self): self.assertEqual(parallel_map(lambda x: x * 2, [1, 2, 3]), [2, 4, 6])
    def test_parallel_map_empty(self): self.assertEqual(parallel_map(lambda x: x, []), [])
    def test_deterministic(self): self.assertEqual(run_sync(lambda: 5), run_sync(lambda: 5))
    def test_many(self): self.assertEqual(parallel_map(lambda x: x + 1, range(10)), list(range(1, 11)))
    def test_parallel_workers(self):
        result = parallel_map(lambda x: x * 2, [1, 2, 3, 4, 5], max_workers=2)
        self.assertEqual(result, [2, 4, 6, 8, 10])
    def test_exception(self):
        with self.assertRaises(ValueError): run_sync(lambda: (_ for _ in ()).throw(ValueError("x")))
    def test_no_crash(self): run_sync(lambda: None)
    def test_single(self): self.assertEqual(parallel_map(lambda x: x, [42]), [42])
