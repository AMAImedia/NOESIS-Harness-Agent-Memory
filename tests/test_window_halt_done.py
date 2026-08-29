import unittest
from noesis_harness.window_halt_done import window_halt_done

class TestWindowHaltDone(unittest.TestCase):
    def test_basic(self): self.assertEqual(list(window_halt_done(sum, iter([1,2,3,4,5]), 3)), [6,9,12])
    def test_empty(self): self.assertEqual(list(window_halt_done(sum, iter([]), 3)), [])
    def test_short(self): self.assertEqual(list(window_halt_done(sum, iter([1,2]), 3)), [])
    def test_exact(self): self.assertEqual(list(window_halt_done(sum, iter([1,2,3]), 3)), [6])
    def test_deterministic(self): self.assertEqual(list(window_halt_done(sum, iter([1,2,3]), 2)), [3,5])
    def test_many(self): self.assertEqual(len(list(window_halt_done(sum, iter(range(10)), 3))), 8)
    def test_no_crash(self): list(window_halt_done(sum, iter([]), 5))
    def test_size_one(self): self.assertEqual(list(window_halt_done(sum, iter([1,2,3]), 1)), [1,2,3])
    def test_lambda(self): self.assertEqual(list(window_halt_done(lambda w: max(w), iter([1,3,2,4,5]), 3)), [3,4,5])
    def test_transform(self): self.assertEqual(list(window_halt_done(lambda w: w[-1], iter([1,2,3,4,5]), 2)), [2,3,4,5])
