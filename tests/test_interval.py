import unittest
from noesis_harness.interval import merge

class TestInterval(unittest.TestCase):
    def test_merge(self): self.assertEqual(merge([(1, 3), (2, 5)]), [(1, 5)])
    def test_disjoint(self): self.assertEqual(merge([(1, 2), (3, 4)]), [(1, 2), (3, 4)])
    def test_empty(self): self.assertEqual(merge([]), [])
    def test_single(self): self.assertEqual(merge([(1, 2)]), [(1, 2)])
    def test_order(self): self.assertEqual(merge([(3, 5), (1, 2)]), [(1, 2), (3, 5)])
    def test_overlap_three(self): self.assertEqual(merge([(1, 4), (2, 5), (4, 6)]), [(1, 6)])
    def test_adjacent(self): self.assertEqual(merge([(1, 2), (2, 3)]), [(1, 3)])
    def test_determinism(self): self.assertEqual(merge([(1, 3), (2, 5)]), merge([(2, 5), (1, 3)]))
    def test_nested(self): self.assertEqual(merge([(1, 10), (3, 4)]), [(1, 10)])
    def test_many(self):
        iv = [(i*2, i*2+1) for i in range(5)]
        self.assertEqual(len(merge(iv)), 5)
