import unittest
from noesis_harness.bucket_done import BucketDone

class TestBucketDone(unittest.TestCase):
    def test_done(self): bd = BucketDone(5); self.assertEqual(bd.done("a", 1), 1)
    def test_existing(self): bd = BucketDone(5); bd.done("a", 1); self.assertEqual(bd.done("a", 2), 2)
    def test_full(self): bd = BucketDone(2); bd.done("a", 1); bd.done("b", 2); self.assertTrue(bd.full()); self.assertIsNone(bd.done("c", 3))
    def test_get(self): bd = BucketDone(5); bd.set("k", 1); self.assertEqual(bd.get("k"), 1)
    def test_get_default(self): self.assertEqual(BucketDone(5).get("x", 5), 5)
    def test_invalidate(self): bd = BucketDone(5); bd.set("a", 1); self.assertTrue(bd.invalidate("a")); self.assertFalse(bd.invalidate("a"))
    def test_clear(self): bd = BucketDone(5); bd.set("a", 1); bd.set("b", 2); self.assertEqual(bd.clear(), 2); self.assertEqual(len(bd), 0)
    def test_len(self): bd = BucketDone(5); bd.set("a", 1); bd.set("b", 2); self.assertEqual(len(bd), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): BucketDone(0)
    def test_deterministic(self): bd = BucketDone(5); bd.set("a", 1); self.assertEqual(bd.get("a"), bd.get("a"))
    def test_many(self): bd = BucketDone(10); [bd.set(f"k{i}", i) for i in range(10)]; self.assertTrue(bd.full())
