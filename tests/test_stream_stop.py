import unittest
from noesis_harness.stream_stop import stream_stop, stream_stop_cached

class TestStreamStop(unittest.TestCase):
    def test_basic(self): self.assertEqual(list(stream_stop(lambda x: x * 2, iter([1,2,3]))), [2,4,6])
    def test_empty(self): self.assertEqual(list(stream_stop(lambda x: x, iter([]))), [])
    def test_cached(self): c = {}; self.assertEqual(list(stream_stop_cached(lambda x: x * 2, iter([1,2,1,3]), c)), [2,4,2,6]); self.assertEqual(len(c), 3)
    def test_cached_empty(self): self.assertEqual(list(stream_stop_cached(lambda x: x, iter([]))), [])
    def test_deterministic(self): self.assertEqual(list(stream_stop(lambda x: x, iter([1,2]))), [1,2])
    def test_many(self): self.assertEqual(list(stream_stop(lambda x: x + 1, iter(range(10)))), list(range(1,11)))
    def test_no_crash(self): list(stream_stop(lambda x: x, iter([])))
    def test_single(self): self.assertEqual(list(stream_stop(lambda x: x + 1, iter([5]))), [6])
    def test_cache_reuse(self):
        c = {}
        list(stream_stop_cached(lambda x: x * 2, iter([1,2]), c))
        list(stream_stop_cached(lambda x: x * 3, iter([1,2]), c))
        self.assertEqual(c[1], 2)
    def test_lambda(self): self.assertEqual(list(stream_stop(lambda x: x ** 2, iter([1,2,3]))), [1,4,9])
