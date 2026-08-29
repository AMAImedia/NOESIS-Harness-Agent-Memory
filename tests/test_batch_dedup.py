import unittest
from noesis_harness.batch_dedup import batch_dedup, batch_dedup_key

class TestBatchDedup(unittest.TestCase):
    def test_basic(self): self.assertEqual(batch_dedup([1, 2, 1, 3, 2]), [1, 2, 3])
    def test_empty(self): self.assertEqual(batch_dedup([]), [])
    def test_single(self): self.assertEqual(batch_dedup([5]), [5])
    def test_all_same(self): self.assertEqual(batch_dedup([1, 1, 1]), [1])
    def test_key(self): self.assertEqual(batch_dedup_key([{"a": 1}, {"a": 2}, {"a": 1}], lambda x: x["a"]), [{"a": 1}, {"a": 2}])
    def test_key_empty(self): self.assertEqual(batch_dedup_key([], lambda x: x), [])
    def test_deterministic(self): self.assertEqual(batch_dedup([1, 2, 1]), [1, 2])
    def test_many(self): self.assertEqual(batch_dedup(list(range(10))), list(range(10)))
    def test_no_mutation(self): a = [1, 2, 1]; batch_dedup(a); self.assertEqual(a, [1, 2, 1])
    def test_order(self): self.assertEqual(batch_dedup([3, 1, 2, 1, 3]), [3, 1, 2])
