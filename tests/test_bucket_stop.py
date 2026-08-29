import unittest
from noesis_harness.bucket_stop import BucketStop

class TestBucketStop(unittest.TestCase):
    def test_stop(self): bs = BucketStop(5); self.assertEqual(bs.stop("a", 1), 1)
    def test_existing(self): bs = BucketStop(5); bs.stop("a", 1); self.assertEqual(bs.stop("a", 2), 2)
    def test_full(self): bs = BucketStop(2); bs.stop("a", 1); bs.stop("b", 2); self.assertTrue(bs.full()); self.assertIsNone(bs.stop("c", 3))
    def test_get(self): bs = BucketStop(5); bs.set("k", 1); self.assertEqual(bs.get("k"), 1)
    def test_get_default(self): self.assertEqual(BucketStop(5).get("x", 5), 5)
    def test_invalidate(self): bs = BucketStop(5); bs.set("a", 1); self.assertTrue(bs.invalidate("a")); self.assertFalse(bs.invalidate("a"))
    def test_clear(self): bs = BucketStop(5); bs.set("a", 1); bs.set("b", 2); self.assertEqual(bs.clear(), 2); self.assertEqual(len(bs), 0)
    def test_len(self): bs = BucketStop(5); bs.set("a", 1); bs.set("b", 2); self.assertEqual(len(bs), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): BucketStop(0)
    def test_deterministic(self): bs = BucketStop(5); bs.set("a", 1); self.assertEqual(bs.get("a"), bs.get("a"))
    def test_many(self): bs = BucketStop(10); [bs.set(f"k{i}", i) for i in range(10)]; self.assertTrue(bs.full())
