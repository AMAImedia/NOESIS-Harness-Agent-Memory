import unittest
from noesis_harness.memoize_tag import TaggedMemo

class TestMemoizeTag(unittest.TestCase):
    def test_put_get(self): m = TaggedMemo(); m.put("k", 1); self.assertEqual(m.get("k"), 1)
    def test_missing(self): self.assertIsNone(TaggedMemo().get("x"))
    def test_invalidate(self): m = TaggedMemo(); m.put("a", 1, "t1"); m.put("b", 2, "t2"); m.invalidate("t1"); self.assertIsNone(m.get("a")); self.assertEqual(m.get("b"), 2)
    def test_clear(self): m = TaggedMemo(); m.put("a", 1); m.put("b", 2); m.clear(); self.assertEqual(len(m), 0)
    def test_len(self): m = TaggedMemo(); m.put("a", 1); m.put("b", 2); self.assertEqual(len(m), 2)
    def test_contains(self): m = TaggedMemo(); m.put("a", 1); self.assertIn("a", m); self.assertNotIn("b", m)
    def test_tag_default(self): m = TaggedMemo(); m.put("a", 1); m.invalidate("default"); self.assertEqual(len(m), 0)
    def test_no_mutation(self): m = TaggedMemo(); m.put("a", 1); m.get("a"); self.assertEqual(len(m), 1)
    def test_determinism(self): m = TaggedMemo(); m.put("a", 1); self.assertEqual(m.get("a"), m.get("a"))
    def test_many(self): m = TaggedMemo(); [m.put(f"k{i}", i) for i in range(5)]; self.assertEqual(len(m), 5)
