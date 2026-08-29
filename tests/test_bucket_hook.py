import unittest
from noesis_harness.bucket_hook import BucketHook

class TestBucketHook(unittest.TestCase):
    def test_hook(self): bh = BucketHook(5); self.assertEqual(bh.hook("a", 1), 1)
    def test_existing(self): bh = BucketHook(5); bh.hook("a", 1); self.assertEqual(bh.hook("a", 2), 2)
    def test_full(self): bh = BucketHook(2); bh.hook("a", 1); bh.hook("b", 2); self.assertTrue(bh.full()); self.assertIsNone(bh.hook("c", 3))
    def test_get(self): bh = BucketHook(5); bh.set("k", 1); self.assertEqual(bh.get("k"), 1)
    def test_get_default(self): self.assertEqual(BucketHook(5).get("x", 5), 5)
    def test_invalidate(self): bh = BucketHook(5); bh.set("a", 1); self.assertTrue(bh.invalidate("a")); self.assertFalse(bh.invalidate("a"))
    def test_clear(self): bh = BucketHook(5); bh.set("a", 1); bh.set("b", 2); self.assertEqual(bh.clear(), 2); self.assertEqual(len(bh), 0)
    def test_len(self): bh = BucketHook(5); bh.set("a", 1); bh.set("b", 2); self.assertEqual(len(bh), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): BucketHook(0)
    def test_deterministic(self): bh = BucketHook(5); bh.set("a", 1); self.assertEqual(bh.get("a"), bh.get("a"))
    def test_many(self): bh = BucketHook(10); [bh.set(f"k{i}", i) for i in range(10)]; self.assertTrue(bh.full())
