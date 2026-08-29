import unittest
from noesis_harness.bucket_halt import BucketHalt

class TestBucketHalt(unittest.TestCase):
    def test_halt(self): bh = BucketHalt(5); self.assertEqual(bh.halt("a", 1), 1)
    def test_existing(self): bh = BucketHalt(5); bh.halt("a", 1); self.assertEqual(bh.halt("a", 2), 2)
    def test_full(self): bh = BucketHalt(2); bh.halt("a", 1); bh.halt("b", 2); self.assertTrue(bh.full()); self.assertIsNone(bh.halt("c", 3))
    def test_get(self): bh = BucketHalt(5); bh.set("k", 1); self.assertEqual(bh.get("k"), 1)
    def test_get_default(self): self.assertEqual(BucketHalt(5).get("x", 5), 5)
    def test_invalidate(self): bh = BucketHalt(5); bh.set("a", 1); self.assertTrue(bh.invalidate("a")); self.assertFalse(bh.invalidate("a"))
    def test_clear(self): bh = BucketHalt(5); bh.set("a", 1); bh.set("b", 2); self.assertEqual(bh.clear(), 2); self.assertEqual(len(bh), 0)
    def test_len(self): bh = BucketHalt(5); bh.set("a", 1); bh.set("b", 2); self.assertEqual(len(bh), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): BucketHalt(0)
    def test_deterministic(self): bh = BucketHalt(5); bh.set("a", 1); self.assertEqual(bh.get("a"), bh.get("a"))
    def test_many(self): bh = BucketHalt(10); [bh.set(f"k{i}", i) for i in range(10)]; self.assertTrue(bh.full())
