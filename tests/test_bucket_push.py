import unittest
from noesis_harness.bucket_push import BucketPush

class TestBucketPush(unittest.TestCase):
    def test_push(self): bp = BucketPush(5); self.assertEqual(bp.push("a", 1), 1)
    def test_existing(self): bp = BucketPush(5); bp.push("a", 1); self.assertEqual(bp.push("a", 2), 2)
    def test_full(self): bp = BucketPush(2); bp.push("a", 1); bp.push("b", 2); self.assertTrue(bp.full()); self.assertIsNone(bp.push("c", 3))
    def test_get(self): bp = BucketPush(5); bp.set("k", 1); self.assertEqual(bp.get("k"), 1)
    def test_get_default(self): self.assertEqual(BucketPush(5).get("x", 5), 5)
    def test_invalidate(self): bp = BucketPush(5); bp.set("a", 1); self.assertTrue(bp.invalidate("a")); self.assertFalse(bp.invalidate("a"))
    def test_clear(self): bp = BucketPush(5); bp.set("a", 1); bp.set("b", 2); self.assertEqual(bp.clear(), 2); self.assertEqual(len(bp), 0)
    def test_len(self): bp = BucketPush(5); bp.set("a", 1); bp.set("b", 2); self.assertEqual(len(bp), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): BucketPush(0)
    def test_deterministic(self): bp = BucketPush(5); bp.set("a", 1); self.assertEqual(bp.get("a"), bp.get("a"))
    def test_many(self): bp = BucketPush(10); [bp.set(f"k{i}", i) for i in range(10)]; self.assertTrue(bp.full())
