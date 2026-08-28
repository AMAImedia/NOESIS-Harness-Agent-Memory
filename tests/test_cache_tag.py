import unittest
from noesis_harness.cache_tag import TagCache

class TestTagCache(unittest.TestCase):
    def test_put_get(self): c = TagCache(); c.put("k", 1, ["t"]); self.assertEqual(c.get("k"), 1)
    def test_invalidate(self): c = TagCache(); c.put("a", 1, ["t"]); c.put("b", 2, ["t"]); self.assertEqual(c.invalidate("t"), 2); self.assertEqual(len(c), 0)
    def test_no_tag(self): c = TagCache(); c.put("k", 1); self.assertEqual(c.get("k"), 1)
    def test_missing_tag(self): self.assertEqual(TagCache().invalidate("nope"), 0)
    def test_partial(self): c = TagCache(); c.put("a", 1, ["t1"]); c.put("b", 2, ["t2"]); c.invalidate("t1"); self.assertEqual(c.get("b"), 2)
    def test_len(self): c = TagCache(); c.put("a", 1); c.put("b", 2); self.assertEqual(len(c), 2)
    def test_overwrite(self): c = TagCache(); c.put("k", 1, ["t"]); c.put("k", 2, ["t"]); self.assertEqual(c.get("k"), 2)
    def test_determinism(self):
        a = TagCache(); b = TagCache(); a.put("k", 1, ["t"]); b.put("k", 1, ["t"]); self.assertEqual(a.get("k"), b.get("k"))
    def test_empty(self): self.assertEqual(len(TagCache()), 0)
    def test_multi_tag(self): c = TagCache(); c.put("k", 1, ["t1", "t2"]); c.invalidate("t1"); self.assertEqual(len(c), 0)
