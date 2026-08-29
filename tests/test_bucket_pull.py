import unittest
from noesis_harness.bucket_pull import BucketPull

class TestBucketPull(unittest.TestCase):
    def test_pull(self): bp = BucketPull(5); self.assertEqual(bp.pull("a", 1), 1)
    def test_existing(self): bp = BucketPull(5); bp.pull("a", 1); self.assertEqual(bp.pull("a", 2), 2)
    def test_full(self): bp = BucketPull(2); bp.pull("a", 1); bp.pull("b", 2); self.assertTrue(bp.full()); self.assertIsNone(bp.pull("c", 3))
    def test_get(self): bp = BucketPull(5); bp.set("k", 1); self.assertEqual(bp.get("k"), 1)
    def test_get_default(self): self.assertEqual(BucketPull(5).get("x", 5), 5)
    def test_invalidate(self): bp = BucketPull(5); bp.set("a", 1); self.assertTrue(bp.invalidate("a")); self.assertFalse(bp.invalidate("a"))
    def test_clear(self): bp = BucketPull(5); bp.set("a", 1); bp.set("b", 2); self.assertEqual(bp.clear(), 2); self.assertEqual(len(bp), 0)
    def test_len(self): bp = BucketPull(5); bp.set("a", 1); bp.set("b", 2); self.assertEqual(len(bp), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): BucketPull(0)
    def test_deterministic(self): bp = BucketPull(5); bp.set("a", 1); self.assertEqual(bp.get("a"), bp.get("a"))
    def test_many(self): bp = BucketPull(10); [bp.set(f"k{i}", i) for i in range(10)]; self.assertTrue(bp.full())
