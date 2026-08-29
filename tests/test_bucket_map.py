import unittest
from noesis_harness.bucket_map import BucketMap

class TestBucketMap(unittest.TestCase):
    def test_mapping(self): bm = BucketMap(5); self.assertEqual(bm.mapping("a", 1), 1)
    def test_existing(self): bm = BucketMap(5); bm.mapping("a", 1); self.assertEqual(bm.mapping("a", 2), 2)
    def test_full(self): bm = BucketMap(2); bm.mapping("a", 1); bm.mapping("b", 2); self.assertTrue(bm.full()); self.assertIsNone(bm.mapping("c", 3))
    def test_get(self): bm = BucketMap(5); bm.set("k", 1); self.assertEqual(bm.get("k"), 1)
    def test_get_default(self): self.assertEqual(BucketMap(5).get("x", 5), 5)
    def test_invalidate(self): bm = BucketMap(5); bm.set("a", 1); self.assertTrue(bm.invalidate("a")); self.assertFalse(bm.invalidate("a"))
    def test_clear(self): bm = BucketMap(5); bm.set("a", 1); bm.set("b", 2); self.assertEqual(bm.clear(), 2); self.assertEqual(len(bm), 0)
    def test_len(self): bm = BucketMap(5); bm.set("a", 1); bm.set("b", 2); self.assertEqual(len(bm), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): BucketMap(0)
    def test_deterministic(self): bm = BucketMap(5); bm.set("a", 1); self.assertEqual(bm.get("a"), bm.get("a"))
    def test_many(self): bm = BucketMap(10); [bm.set(f"k{i}", i) for i in range(10)]; self.assertTrue(bm.full())
