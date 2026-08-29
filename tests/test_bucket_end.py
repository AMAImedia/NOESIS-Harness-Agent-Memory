import unittest
from noesis_harness.bucket_end import BucketEnd

class TestBucketEnd(unittest.TestCase):
    def test_end(self): be = BucketEnd(5); self.assertEqual(be.end("a", 1), 1)
    def test_existing(self): be = BucketEnd(5); be.end("a", 1); self.assertEqual(be.end("a", 2), 2)
    def test_full(self): be = BucketEnd(2); be.end("a", 1); be.end("b", 2); self.assertTrue(be.full()); self.assertIsNone(be.end("c", 3))
    def test_get(self): be = BucketEnd(5); be.set("k", 1); self.assertEqual(be.get("k"), 1)
    def test_get_default(self): self.assertEqual(BucketEnd(5).get("x", 5), 5)
    def test_invalidate(self): be = BucketEnd(5); be.set("a", 1); self.assertTrue(be.invalidate("a")); self.assertFalse(be.invalidate("a"))
    def test_clear(self): be = BucketEnd(5); be.set("a", 1); be.set("b", 2); self.assertEqual(be.clear(), 2); self.assertEqual(len(be), 0)
    def test_len(self): be = BucketEnd(5); be.set("a", 1); be.set("b", 2); self.assertEqual(len(be), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): BucketEnd(0)
    def test_deterministic(self): be = BucketEnd(5); be.set("a", 1); self.assertEqual(be.get("a"), be.get("a"))
    def test_many(self): be = BucketEnd(10); [be.set(f"k{i}", i) for i in range(10)]; self.assertTrue(be.full())
