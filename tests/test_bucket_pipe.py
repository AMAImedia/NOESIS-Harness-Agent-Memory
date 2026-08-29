import unittest
from noesis_harness.bucket_pipe import BucketPipe

class TestBucketPipe(unittest.TestCase):
    def test_pipe(self): bp = BucketPipe(5); self.assertEqual(bp.pipe("a", 1), 1)
    def test_existing(self): bp = BucketPipe(5); bp.pipe("a", 1); self.assertEqual(bp.pipe("a", 2), 2)
    def test_full(self): bp = BucketPipe(2); bp.pipe("a", 1); bp.pipe("b", 2); self.assertTrue(bp.full()); self.assertIsNone(bp.pipe("c", 3))
    def test_get(self): bp = BucketPipe(5); bp.set("k", 1); self.assertEqual(bp.get("k"), 1)
    def test_get_default(self): self.assertEqual(BucketPipe(5).get("x", 5), 5)
    def test_invalidate(self): bp = BucketPipe(5); bp.set("a", 1); self.assertTrue(bp.invalidate("a")); self.assertFalse(bp.invalidate("a"))
    def test_clear(self): bp = BucketPipe(5); bp.set("a", 1); bp.set("b", 2); self.assertEqual(bp.clear(), 2); self.assertEqual(len(bp), 0)
    def test_len(self): bp = BucketPipe(5); bp.set("a", 1); bp.set("b", 2); self.assertEqual(len(bp), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): BucketPipe(0)
    def test_deterministic(self): bp = BucketPipe(5); bp.set("a", 1); self.assertEqual(bp.get("a"), bp.get("a"))
    def test_many(self): bp = BucketPipe(10); [bp.set(f"k{i}", i) for i in range(10)]; self.assertTrue(bp.full())
