import unittest
from noesis_harness.stream_batch import stream_batch, stream_chunk

class TestStreamBatch(unittest.TestCase):
    def test_batch(self): self.assertEqual(list(stream_batch(iter([1,2,3,4,5]), 2)), [[1,2],[3,4],[5]])
    def test_chunk(self): self.assertEqual(list(stream_chunk(iter([1,2,3,4,5]), 2)), [[1,2],[3,4],[5]])
    def test_empty(self): self.assertEqual(list(stream_batch(iter([]), 2)), [])
    def test_exact(self): self.assertEqual(list(stream_batch(iter([1,2,3]), 3)), [[1,2,3]])
    def test_deterministic(self): self.assertEqual(list(stream_batch(iter([1,2,3]), 2)), list(stream_batch(iter([1,2,3]), 2)))
    def test_many(self): self.assertEqual(len(list(stream_batch(iter(range(100)), 10))), 10)
    def test_single(self): self.assertEqual(list(stream_batch(iter([5]), 10)), [[5]])
    def test_size_one(self): self.assertEqual(list(stream_batch(iter([1,2,3]), 1)), [[1],[2],[3]])
    def test_no_crash(self): list(stream_batch(iter([]), 5))
    def test_remainder(self): self.assertEqual(len(list(stream_batch(iter(range(7)), 3))), 3)
