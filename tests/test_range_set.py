import unittest
from noesis_harness.range_set import RangeSet

class TestRangeSet(unittest.TestCase):
    def test_contains(self): r = RangeSet(); r.add(1, 5); self.assertTrue(4 in r); self.assertFalse(6 in r)
    def test_merge(self): r = RangeSet(); r.add(1, 3); r.add(2, 5); self.assertEqual(r.ranges(), [(1, 5)])
    def test_swap(self): r = RangeSet(); r.add(5, 1); self.assertEqual(r.ranges(), [(1, 5)])
    def test_disjoint(self): r = RangeSet(); r.add(1, 2); r.add(4, 5); self.assertEqual(len(r.ranges()), 2)
    def test_empty(self): self.assertEqual(RangeSet().ranges(), [])
    def test_edge(self): r = RangeSet(); r.add(1, 5); self.assertTrue(1 in r); self.assertTrue(5 in r)
    def test_determinism(self): a = RangeSet(); b = RangeSet(); a.add(1, 3); b.add(1, 3); self.assertEqual(a.ranges(), b.ranges())
    def test_many(self):
        r = RangeSet()
        for i in range(5): r.add(i*10, i*10+5)
        self.assertEqual(len(r.ranges()), 5)
    def test_add_twice(self): r = RangeSet(); r.add(1, 3); r.add(1, 3); self.assertEqual(r.ranges(), [(1, 3)])
    def test_gap(self): r = RangeSet(); r.add(1, 2); r.add(4, 5); self.assertFalse(3 in r)
