import unittest
from noesis_harness.skip_list import SkipList

class TestSkipList(unittest.TestCase):
    def test_insert(self): s = SkipList(1); s.insert(3); self.assertIn(3, s)
    def test_missing(self): s = SkipList(1); self.assertNotIn(5, s)
    def test_sorted(self): s = SkipList(2); [s.insert(i) for i in [5, 1, 3, 2, 4]]; self.assertEqual(s.to_list(), [1, 2, 3, 4, 5])
    def test_dedup(self): s = SkipList(3); s.insert(1); s.insert(1); self.assertEqual(s.to_list(), [1])
    def test_order(self): s = SkipList(4); s.insert(1); s.insert(2); self.assertEqual(s.to_list(), [1, 2])
    def test_determinism(self):
        a = SkipList(7); b = SkipList(7)
        for v in [9, 3, 5]: a.insert(v); b.insert(v)
        self.assertEqual(a.to_list(), b.to_list())
    def test_empty(self): self.assertEqual(SkipList().to_list(), [])
    def test_strings(self): s = SkipList(5); s.insert("b"); s.insert("a"); self.assertEqual(s.to_list(), ["a", "b"])
    def test_many(self):
        s = SkipList(9)
        for i in range(20, 0, -1): s.insert(i)
        self.assertEqual(s.to_list(), list(range(1, 21)))
    def test_contains_many(self):
        s = SkipList(11)
        for i in range(10): s.insert(i)
        self.assertTrue(all(i in s for i in range(10)))
        self.assertFalse(99 in s)
