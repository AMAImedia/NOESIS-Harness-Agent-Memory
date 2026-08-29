import unittest
from noesis_harness.bucket_hold import BucketHold

class TestBucketHold(unittest.TestCase):
    def test_hold(self): bh = BucketHold(5); self.assertEqual(bh.hold("a", 1), 1)
    def test_existing(self): bh = BucketHold(5); bh.hold("a", 1); self.assertEqual(bh.hold("a", 2), 2)
    def test_full(self): bh = BucketHold(2); bh.hold("a", 1); bh.hold("b", 2); self.assertTrue(bh.full()); self.assertIsNone(bh.hold("c", 3))
    def test_get(self): bh = BucketHold(5); bh.set("k", 1); self.assertEqual(bh.get("k"), 1)
    def test_get_default(self): self.assertEqual(BucketHold(5).get("x", 5), 5)
    def test_invalidate(self): bh = BucketHold(5); bh.set("a", 1); self.assertTrue(bh.invalidate("a")); self.assertFalse(bh.invalidate("a"))
    def test_clear(self): bh = BucketHold(5); bh.set("a", 1); bh.set("b", 2); self.assertEqual(bh.clear(), 2); self.assertEqual(len(bh), 0)
    def test_len(self): bh = BucketHold(5); bh.set("a", 1); bh.set("b", 2); self.assertEqual(len(bh), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): BucketHold(0)
    def test_deterministic(self): bh = BucketHold(5); bh.set("a", 1); self.assertEqual(bh.get("a"), bh.get("a"))
    def test_many(self): bh = BucketHold(10); [bh.set(f"k{i}", i) for i in range(10)]; self.assertTrue(bh.full())
