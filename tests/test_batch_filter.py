import unittest
from noesis_harness.batch_filter import batch_filter, batch_select, batch_reject

class TestBatchFilter(unittest.TestCase):
    def test_filter(self): batches = list(batch_filter(iter([1,2,3,4,5]), lambda x: x > 2, 2)); self.assertEqual(batches, [[3,4],[5]])
    def test_select(self): self.assertEqual(batch_select([1,2,3,4,5], lambda x: x > 2), [3,4,5])
    def test_reject(self): self.assertEqual(batch_reject([1,2,3,4,5], lambda x: x > 2), [1,2])
    def test_empty(self): self.assertEqual(list(batch_filter(iter([]), lambda x: True, 2)), [])
    def test_select_empty(self): self.assertEqual(batch_select([], lambda x: True), [])
    def test_reject_empty(self): self.assertEqual(batch_reject([], lambda x: True), [])
    def test_deterministic(self): self.assertEqual(batch_select([1,2,3], lambda x: x > 1), [2,3])
    def test_many(self): self.assertEqual(len(list(batch_filter(iter(range(100)), lambda x: x % 2 == 0, 10))), 5)
    def test_no_crash(self): list(batch_filter(iter([]), lambda x: True, 5))
    def test_single(self): self.assertEqual(batch_select([5], lambda x: x == 5), [5])
