import unittest
from noesis_harness.chunked_read import chunked, head, tail

class TestChunkedRead(unittest.TestCase):
    def test_chunked(self): self.assertEqual(list(chunked([1,2,3,4], 2)), [[1,2],[3,4]])
    def test_remainder(self): self.assertEqual(list(chunked([1,2,3], 2)), [[1,2],[3]])
    def test_empty(self): self.assertEqual(list(chunked([], 2)), [])
    def test_invalid(self):
        with self.assertRaises(ValueError): list(chunked([1], 0))
    def test_head(self): self.assertEqual(head([1,2,3,4], 2), [1,2])
    def test_head_more(self): self.assertEqual(head([1,2], 10), [1,2])
    def test_head_empty(self): self.assertEqual(head([], 5), [])
    def test_tail(self): self.assertEqual(tail([1,2,3,4], 2), [3,4])
    def test_tail_more(self): self.assertEqual(tail([1,2], 10), [1,2])
    def test_deterministic(self): self.assertEqual(list(chunked([1,2,3], 2)), list(chunked([1,2,3], 2)))
    def test_many(self): self.assertEqual(len(list(chunked(range(100), 10))), 10)
    def test_size_one(self): self.assertEqual(list(chunked([1,2,3], 1)), [[1],[2],[3]])
