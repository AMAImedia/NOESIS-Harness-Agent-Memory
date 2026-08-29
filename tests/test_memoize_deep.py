import unittest
from noesis_harness.memoize_deep import MemoDeep

class TestMemoDeep(unittest.TestCase):
    def test_put_get(self): m = MemoDeep(); m.put(1, "a", "b"); self.assertEqual(m.get("a", "b"), 1)
    def test_missing(self): self.assertIsNone(MemoDeep().get("x", "y"))
    def test_invalidate(self): m = MemoDeep(); m.put(1, "a", "b"); self.assertTrue(m.invalidate("a", "b")); self.assertIsNone(m.get("a", "b"))
    def test_invalidate_missing(self): self.assertFalse(MemoDeep().invalidate("x", "y"))
    def test_deep(self): m = MemoDeep(); m.put(42, "x", "y", "z"); self.assertEqual(m.get("x", "y", "z"), 42)
    def test_len(self): m = MemoDeep(); m.put(1, "a"); m.put(2, "b"); self.assertEqual(len(m), 2)
    def test_no_mutation(self): m = MemoDeep(); m.put(1, "a"); m.get("a"); self.assertEqual(len(m), 1)
    def test_deterministic(self): m = MemoDeep(); m.put(5, "k"); self.assertEqual(m.get("k"), m.get("k"))
    def test_many(self): m = MemoDeep(); [m.put(i, f"k{i}") for i in range(5)]; self.assertEqual(len(m), 5)
    def test_overwrite(self): m = MemoDeep(); m.put(1, "a"); m.put(2, "a"); self.assertEqual(m.get("a"), 2)
