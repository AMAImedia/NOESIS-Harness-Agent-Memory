import unittest
from noesis_harness.memoize_version import MemoVersion

class TestMemoVersion(unittest.TestCase):
    def test_put_get(self): m = MemoVersion(); m.put("k", 1); self.assertEqual(m.get("k"), 1)
    def test_missing(self): self.assertIsNone(MemoVersion().get("x"))
    def test_version(self): m = MemoVersion(); v = m.put("k", 1); self.assertEqual(v, 1); v2 = m.put("k", 2); self.assertEqual(v2, 2)
    def test_invalidate(self): m = MemoVersion(); m.put("a", 1); self.assertTrue(m.invalidate("a")); self.assertFalse(m.invalidate("a"))
    def test_clear(self): m = MemoVersion(); m.put("a", 1); m.put("b", 2); self.assertEqual(m.clear(), 2); self.assertEqual(len(m), 0)
    def test_len(self): m = MemoVersion(); m.put("a", 1); m.put("b", 2); self.assertEqual(len(m), 2)
    def test_contains(self): m = MemoVersion(); m.put("a", 1); self.assertIn("a", m); self.assertNotIn("b", m)
    def test_deterministic(self): m = MemoVersion(); m.put("a", 1); self.assertEqual(m.get("a"), m.get("a"))
    def test_many(self): m = MemoVersion(); [m.put(f"k{i}", i) for i in range(5)]; self.assertEqual(len(m), 5)
    def test_overwrite(self): m = MemoVersion(); m.put("a", 1); m.put("a", 2); self.assertEqual(m.get("a"), 2); self.assertEqual(m.version("a"), 2)
