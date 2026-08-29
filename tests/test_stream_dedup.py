import unittest
from noesis_harness.stream_dedup import stream_dedup, stream_dedup_key

class TestStreamDedup(unittest.TestCase):
    def test_basic(self): self.assertEqual(list(stream_dedup(iter([1, 2, 1, 3, 2]))), [1, 2, 3])
    def test_empty(self): self.assertEqual(list(stream_dedup(iter([]))), [])
    def test_single(self): self.assertEqual(list(stream_dedup(iter([5]))), [5])
    def test_all_same(self): self.assertEqual(list(stream_dedup(iter([1, 1, 1]))), [1])
    def test_key(self): self.assertEqual(list(stream_dedup_key(iter([1, 2, 3, 4]), lambda x: x % 2)), [1, 2])
    def test_key_empty(self): self.assertEqual(list(stream_dedup_key(iter([]), lambda x: x)), [])
    def test_deterministic(self): self.assertEqual(list(stream_dedup(iter([1, 2, 1]))), [1, 2])
    def test_many(self): self.assertEqual(list(stream_dedup(iter(range(10)))), list(range(10)))
    def test_no_crash(self): list(stream_dedup(iter([])))
    def test_order(self): self.assertEqual(list(stream_dedup(iter([3, 1, 2, 1, 3]))), [3, 1, 2])
