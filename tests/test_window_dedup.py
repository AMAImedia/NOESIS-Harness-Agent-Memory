import unittest
from noesis_harness.window_dedup import window_dedup

class TestWindowDedup(unittest.TestCase):
    def test_basic(self): self.assertEqual(list(window_dedup(iter([1, 2, 1, 3, 2]), 3)), [1, 2, 3])
    def test_empty(self): self.assertEqual(list(window_dedup(iter([]), 3)), [])
    def test_single(self): self.assertEqual(list(window_dedup(iter([5]), 3)), [5])
    def test_all_same(self): self.assertEqual(list(window_dedup(iter([1, 1, 1]), 3)), [1])
    def test_window_1(self): self.assertEqual(list(window_dedup(iter([1, 2, 1, 3]), 1)), [1, 2, 1, 3])
    def test_window_2(self): self.assertEqual(list(window_dedup(iter([1, 2, 1, 3]), 2)), [1, 2, 3])
    def test_deterministic(self): self.assertEqual(list(window_dedup(iter([1, 2, 1]), 3)), [1, 2])
    def test_many(self): self.assertEqual(list(window_dedup(iter(range(10)), 5)), list(range(10)))
    def test_no_crash(self): list(window_dedup(iter([]), 5))
    def test_repeats(self): self.assertEqual(list(window_dedup(iter([1, 1, 2, 2, 3, 3]), 2)), [1, 2, 3])
