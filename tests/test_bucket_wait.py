import unittest
from noesis_harness.bucket_wait import BucketWait

class TestBucketWait(unittest.TestCase):
    def test_wait(self): bw = BucketWait(5); self.assertEqual(bw.wait("a", 1), 1)
    def test_existing(self): bw = BucketWait(5); bw.wait("a", 1); self.assertEqual(bw.wait("a", 2), 2)
    def test_full(self): bw = BucketWait(2); bw.wait("a", 1); bw.wait("b", 2); self.assertTrue(bw.full()); self.assertIsNone(bw.wait("c", 3))
    def test_get(self): bw = BucketWait(5); bw.set("k", 1); self.assertEqual(bw.get("k"), 1)
    def test_get_default(self): self.assertEqual(BucketWait(5).get("x", 5), 5)
    def test_invalidate(self): bw = BucketWait(5); bw.set("a", 1); self.assertTrue(bw.invalidate("a")); self.assertFalse(bw.invalidate("a"))
    def test_clear(self): bw = BucketWait(5); bw.set("a", 1); bw.set("b", 2); self.assertEqual(bw.clear(), 2); self.assertEqual(len(bw), 0)
    def test_len(self): bw = BucketWait(5); bw.set("a", 1); bw.set("b", 2); self.assertEqual(len(bw), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): BucketWait(0)
    def test_deterministic(self): bw = BucketWait(5); bw.set("a", 1); self.assertEqual(bw.get("a"), bw.get("a"))
    def test_many(self): bw = BucketWait(10); [bw.set(f"k{i}", i) for i in range(10)]; self.assertTrue(bw.full())
