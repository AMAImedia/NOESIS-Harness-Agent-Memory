import unittest
from noesis_harness.bucket_proxy import BucketProxy

class TestBucketProxy(unittest.TestCase):
    def test_get_set(self): bp = BucketProxy(5); bp.set("k", 1); self.assertEqual(bp.get("k"), 1)
    def test_missing(self): self.assertIsNone(BucketProxy(5).get("x"))
    def test_default(self): self.assertEqual(BucketProxy(5).get("x", 5), 5)
    def test_full(self): bp = BucketProxy(2); bp.set("a", 1); bp.set("b", 2); self.assertTrue(bp.full()); self.assertFalse(bp.set("c", 3))
    def test_invalidate(self): bp = BucketProxy(5); bp.set("a", 1); self.assertTrue(bp.invalidate("a")); self.assertFalse(bp.invalidate("a"))
    def test_clear(self): bp = BucketProxy(5); bp.set("a", 1); bp.set("b", 2); self.assertEqual(bp.clear(), 2); self.assertEqual(len(bp), 0)
    def test_len(self): bp = BucketProxy(5); bp.set("a", 1); bp.set("b", 2); self.assertEqual(len(bp), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): BucketProxy(0)
    def test_deterministic(self): bp = BucketProxy(5); bp.set("a", 1); self.assertEqual(bp.get("a"), bp.get("a"))
    def test_many(self): bp = BucketProxy(10); [bp.set(f"k{i}", i) for i in range(10)]; self.assertTrue(bp.full())
