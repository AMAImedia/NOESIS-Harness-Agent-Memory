import unittest
from noesis_harness.bucket_wrap import BucketWrap

class TestBucketWrap(unittest.TestCase):
    def test_wrap(self): bw = BucketWrap(5); self.assertEqual(bw.wrap("a", 1), 1)
    def test_existing(self): bw = BucketWrap(5); bw.wrap("a", 1); self.assertEqual(bw.wrap("a", 2), 2)
    def test_full(self): bw = BucketWrap(2); bw.wrap("a", 1); bw.wrap("b", 2); self.assertTrue(bw.full()); self.assertIsNone(bw.wrap("c", 3))
    def test_get(self): bw = BucketWrap(5); bw.set("k", 1); self.assertEqual(bw.get("k"), 1)
    def test_get_default(self): self.assertEqual(BucketWrap(5).get("x", 5), 5)
    def test_invalidate(self): bw = BucketWrap(5); bw.set("a", 1); self.assertTrue(bw.invalidate("a")); self.assertFalse(bw.invalidate("a"))
    def test_clear(self): bw = BucketWrap(5); bw.set("a", 1); bw.set("b", 2); self.assertEqual(bw.clear(), 2); self.assertEqual(len(bw), 0)
    def test_len(self): bw = BucketWrap(5); bw.set("a", 1); bw.set("b", 2); self.assertEqual(len(bw), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): BucketWrap(0)
    def test_deterministic(self): bw = BucketWrap(5); bw.set("a", 1); self.assertEqual(bw.get("a"), bw.get("a"))
    def test_many(self): bw = BucketWrap(10); [bw.set(f"k{i}", i) for i in range(10)]; self.assertTrue(bw.full())
