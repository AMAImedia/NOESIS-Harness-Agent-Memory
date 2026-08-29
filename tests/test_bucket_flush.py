import unittest
from noesis_harness.bucket_flush import BucketFlush

class TestBucketFlush(unittest.TestCase):
    def test_flush(self): bf = BucketFlush(5); self.assertEqual(bf.flush("a", 1), 1)
    def test_existing(self): bf = BucketFlush(5); bf.flush("a", 1); self.assertEqual(bf.flush("a", 2), 2)
    def test_full(self): bf = BucketFlush(2); bf.flush("a", 1); bf.flush("b", 2); self.assertTrue(bf.full()); self.assertIsNone(bf.flush("c", 3))
    def test_get(self): bf = BucketFlush(5); bf.set("k", 1); self.assertEqual(bf.get("k"), 1)
    def test_get_default(self): self.assertEqual(BucketFlush(5).get("x", 5), 5)
    def test_invalidate(self): bf = BucketFlush(5); bf.set("a", 1); self.assertTrue(bf.invalidate("a")); self.assertFalse(bf.invalidate("a"))
    def test_clear(self): bf = BucketFlush(5); bf.set("a", 1); bf.set("b", 2); self.assertEqual(bf.clear(), 2); self.assertEqual(len(bf), 0)
    def test_len(self): bf = BucketFlush(5); bf.set("a", 1); bf.set("b", 2); self.assertEqual(len(bf), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): BucketFlush(0)
    def test_deterministic(self): bf = BucketFlush(5); bf.set("a", 1); self.assertEqual(bf.get("a"), bf.get("a"))
    def test_many(self): bf = BucketFlush(10); [bf.set(f"k{i}", i) for i in range(10)]; self.assertTrue(bf.full())
