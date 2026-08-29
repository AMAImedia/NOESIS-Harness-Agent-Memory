import unittest
from noesis_harness.bucket_simple import BucketSimple

class TestBucketSimple(unittest.TestCase):
    def test_remember(self): bs = BucketSimple(5); self.assertEqual(bs.remember("a", 1), 1)
    def test_existing(self): bs = BucketSimple(5); bs.remember("a", 1); self.assertEqual(bs.remember("a", 2), 2)
    def test_full(self): bs = BucketSimple(2); bs.remember("a", 1); bs.remember("b", 2); self.assertTrue(bs.full()); self.assertIsNone(bs.remember("c", 3))
    def test_get(self): bs = BucketSimple(5); bs.set("k", 1); self.assertEqual(bs.get("k"), 1)
    def test_get_default(self): self.assertEqual(BucketSimple(5).get("x", 5), 5)
    def test_invalidate(self): bs = BucketSimple(5); bs.set("a", 1); self.assertTrue(bs.invalidate("a")); self.assertFalse(bs.invalidate("a"))
    def test_clear(self): bs = BucketSimple(5); bs.set("a", 1); bs.set("b", 2); self.assertEqual(bs.clear(), 2); self.assertEqual(len(bs), 0)
    def test_len(self): bs = BucketSimple(5); bs.set("a", 1); bs.set("b", 2); self.assertEqual(len(bs), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): BucketSimple(0)
    def test_deterministic(self): bs = BucketSimple(5); bs.set("a", 1); self.assertEqual(bs.get("a"), bs.get("a"))
    def test_many(self): bs = BucketSimple(10); [bs.set(f"k{i}", i) for i in range(10)]; self.assertTrue(bs.full())
