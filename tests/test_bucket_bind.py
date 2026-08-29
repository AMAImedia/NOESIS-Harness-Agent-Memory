import unittest
from noesis_harness.bucket_bind import BucketBind

class TestBucketBind(unittest.TestCase):
    def test_binding(self): bb = BucketBind(5); self.assertEqual(bb.binding("a", 1), 1)
    def test_existing(self): bb = BucketBind(5); bb.binding("a", 1); self.assertEqual(bb.binding("a", 2), 2)
    def test_full(self): bb = BucketBind(2); bb.binding("a", 1); bb.binding("b", 2); self.assertTrue(bb.full()); self.assertIsNone(bb.binding("c", 3))
    def test_get(self): bb = BucketBind(5); bb.set("k", 1); self.assertEqual(bb.get("k"), 1)
    def test_get_default(self): self.assertEqual(BucketBind(5).get("x", 5), 5)
    def test_invalidate(self): bb = BucketBind(5); bb.set("a", 1); self.assertTrue(bb.invalidate("a")); self.assertFalse(bb.invalidate("a"))
    def test_clear(self): bb = BucketBind(5); bb.set("a", 1); bb.set("b", 2); self.assertEqual(bb.clear(), 2); self.assertEqual(len(bb), 0)
    def test_len(self): bb = BucketBind(5); bb.set("a", 1); bb.set("b", 2); self.assertEqual(len(bb), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): BucketBind(0)
    def test_deterministic(self): bb = BucketBind(5); bb.set("a", 1); self.assertEqual(bb.get("a"), bb.get("a"))
    def test_many(self): bb = BucketBind(10); [bb.set(f"k{i}", i) for i in range(10)]; self.assertTrue(bb.full())
