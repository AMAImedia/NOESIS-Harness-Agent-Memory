import unittest
from noesis_harness.bucket_exit import BucketExit

class TestBucketExit(unittest.TestCase):
    def test_exit(self): be = BucketExit(5); self.assertEqual(be.exit("a", 1), 1)
    def test_existing(self): be = BucketExit(5); be.exit("a", 1); self.assertEqual(be.exit("a", 2), 2)
    def test_full(self): be = BucketExit(2); be.exit("a", 1); be.exit("b", 2); self.assertTrue(be.full()); self.assertIsNone(be.exit("c", 3))
    def test_get(self): be = BucketExit(5); be.set("k", 1); self.assertEqual(be.get("k"), 1)
    def test_get_default(self): self.assertEqual(BucketExit(5).get("x", 5), 5)
    def test_invalidate(self): be = BucketExit(5); be.set("a", 1); self.assertTrue(be.invalidate("a")); self.assertFalse(be.invalidate("a"))
    def test_clear(self): be = BucketExit(5); be.set("a", 1); be.set("b", 2); self.assertEqual(be.clear(), 2); self.assertEqual(len(be), 0)
    def test_len(self): be = BucketExit(5); be.set("a", 1); be.set("b", 2); self.assertEqual(len(be), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): BucketExit(0)
    def test_deterministic(self): be = BucketExit(5); be.set("a", 1); self.assertEqual(be.get("a"), be.get("a"))
    def test_many(self): be = BucketExit(10); [be.set(f"k{i}", i) for i in range(10)]; self.assertTrue(be.full())
