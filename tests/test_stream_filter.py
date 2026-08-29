import unittest
from noesis_harness.stream_filter import filter_stream, take_while, drop_while

class TestStreamFilter(unittest.TestCase):
    def test_filter(self): self.assertEqual(list(filter_stream([1,2,3,4,5], lambda x: x > 2)), [3,4,5])
    def test_filter_empty(self): self.assertEqual(list(filter_stream([], lambda x: True)), [])
    def test_take_while(self): self.assertEqual(list(take_while([1,2,3,4,5], lambda x: x < 3)), [1,2])
    def test_take_while_all(self): self.assertEqual(list(take_while([1,2,3], lambda x: True)), [1,2,3])
    def test_drop_while(self): self.assertEqual(list(drop_while([1,2,3,4,5], lambda x: x < 3)), [3,4,5])
    def test_drop_while_none(self): self.assertEqual(list(drop_while([1,2,3], lambda x: False)), [1,2,3])
    def test_deterministic(self): self.assertEqual(list(filter_stream([1,2,3], lambda x: x > 1)), [2,3])
    def test_many(self): self.assertEqual(list(filter_stream(range(10), lambda x: x % 2 == 0)), [0,2,4,6,8])
    def test_no_crash(self): list(filter_stream([], lambda x: True))
    def test_single(self): self.assertEqual(list(filter_stream([5], lambda x: x == 5)), [5])
