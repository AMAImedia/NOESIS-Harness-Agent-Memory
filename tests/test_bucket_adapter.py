import unittest
from noesis_harness.bucket_adapter import BucketAdapter

class TestBucketAdapter(unittest.TestCase):
    def test_adapt(self): ba = BucketAdapter(5); self.assertEqual(ba.adapt("a", 1), 1)
    def test_existing(self): ba = BucketAdapter(5); ba.adapt("a", 1); self.assertEqual(ba.adapt("a", 2), 2)
    def test_full(self): ba = BucketAdapter(2); ba.adapt("a", 1); ba.adapt("b", 2); self.assertTrue(ba.full()); self.assertIsNone(ba.adapt("c", 3))
    def test_get(self): ba = BucketAdapter(5); ba.set("k", 1); self.assertEqual(ba.get("k"), 1)
    def test_get_default(self): self.assertEqual(BucketAdapter(5).get("x", 5), 5)
    def test_invalidate(self): ba = BucketAdapter(5); ba.set("a", 1); self.assertTrue(ba.invalidate("a")); self.assertFalse(ba.invalidate("a"))
    def test_clear(self): ba = BucketAdapter(5); ba.set("a", 1); ba.set("b", 2); self.assertEqual(ba.clear(), 2); self.assertEqual(len(ba), 0)
    def test_len(self): ba = BucketAdapter(5); ba.set("a", 1); ba.set("b", 2); self.assertEqual(len(ba), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): BucketAdapter(0)
    def test_deterministic(self): ba = BucketAdapter(5); ba.set("a", 1); self.assertEqual(ba.get("a"), ba.get("a"))
    def test_many(self): ba = BucketAdapter(10); [ba.set(f"k{i}", i) for i in range(10)]; self.assertTrue(ba.full())
