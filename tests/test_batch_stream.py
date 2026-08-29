import unittest
from noesis_harness.batch_stream import batch_process, batch_map

class TestBatchStream(unittest.TestCase):
    def test_process(self): batches = list(batch_process(iter([1,2,3,4,5]), lambda x: x * 2, 2)); self.assertEqual(batches, [[2,4],[6,8],[10]])
    def test_map(self): self.assertEqual(batch_map(lambda x: x + 1, [1,2,3,4], 2), [2,3,4,5])
    def test_empty(self): self.assertEqual(list(batch_process(iter([]), lambda x: x, 2)), [])
    def test_map_empty(self): self.assertEqual(batch_map(lambda x: x, [], 2), [])
    def test_deterministic(self): self.assertEqual(batch_map(lambda x: x, [1,2,3], 2), [1,2,3])
    def test_many(self): self.assertEqual(len(list(batch_process(iter(range(100)), lambda x: x, 10))), 10)
    def test_single(self): self.assertEqual(batch_map(lambda x: x, [5], 10), [5])
    def test_exact(self): self.assertEqual(list(batch_process(iter([1,2,3]), lambda x: x, 3)), [[1,2,3]])
    def test_no_crash(self): list(batch_process(iter([]), lambda x: x, 5))
    def test_remainder(self): self.assertEqual(len(list(batch_process(iter(range(7)), lambda x: x, 3))), 3)
