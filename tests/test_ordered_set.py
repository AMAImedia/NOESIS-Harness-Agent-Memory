import unittest
from noesis_harness.ordered_set import OrderedSet

class TestOrderedSet(unittest.TestCase):
    def test_add_contains(self): s = OrderedSet(); s.add("a"); self.assertIn("a", s)
    def test_order(self): s = OrderedSet(); s.add("c"); s.add("a"); s.add("b"); self.assertEqual(s.to_list(), ["c", "a", "b"])
    def test_discard(self): s = OrderedSet([1, 2]); s.discard(1); self.assertNotIn(1, s); self.assertEqual(len(s), 1)
    def test_len(self): s = OrderedSet([1, 2, 3]); self.assertEqual(len(s), 3)
    def test_duplicate_no_dup(self): s = OrderedSet(); s.add("x"); s.add("x"); self.assertEqual(len(s), 1)
    def test_init_iterable(self): s = OrderedSet([3, 1, 2]); self.assertEqual(s.to_list(), [3, 1, 2])
    def test_discard_missing(self): s = OrderedSet(); self.assertFalse(s.discard("nope"))
    def test_contains_false(self): s = OrderedSet([1]); self.assertNotIn(2, s)
    def test_empty(self): s = OrderedSet(); self.assertEqual(s.to_list(), []); self.assertEqual(len(s), 0)
    def test_determinism(self):
        a = OrderedSet([1, 2, 3]); b = OrderedSet([1, 2, 3]); self.assertEqual(a.to_list(), b.to_list())
