import unittest
from noesis_harness.list_util import flatten, unique, compact, chunk, first, last

class TestListUtil(unittest.TestCase):
    def test_flatten(self): self.assertEqual(flatten([1, [2, 3], 4]), [1, 2, 3, 4])
    def test_flatten_deep(self): self.assertEqual(flatten([1, [2, [3]]]), [1, 2, 3])
    def test_unique(self): self.assertEqual(unique([1, 2, 1, 3, 2]), [1, 2, 3])
    def test_compact(self): self.assertEqual(compact([1, None, 2, "", 3, 0]), [1, 2, 3])
    def test_chunk(self): self.assertEqual(chunk([1, 2, 3, 4], 2), [[1, 2], [3, 4]])
    def test_first(self): self.assertEqual(first([1, 2, 3]), 1)
    def test_first_empty(self): self.assertIsNone(first([]))
    def test_last(self): self.assertEqual(last([1, 2, 3]), 3)
    def test_last_empty(self): self.assertIsNone(last([]))
    def test_determinism(self): self.assertEqual(unique([1, 2, 1]), unique([1, 2, 1]))
