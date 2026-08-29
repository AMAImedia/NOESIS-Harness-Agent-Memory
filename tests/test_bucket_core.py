import unittest
from noesis_harness.bucket_core import BucketCore

class TestBucketCore(unittest.TestCase):
    def test_core(self): bc = BucketCore(5); self.assertEqual(bc.core("a", 1), 1)
    def test_existing(self): bc = BucketCore(5); bc.core("a", 1); self.assertEqual(bc.core("a", 2), 2)
    def test_full(self): bc = BucketCore(2); bc.core("a", 1); bc.core("b", 2); self.assertTrue(bc.full()); self.assertIsNone(bc.core("c", 3))
    def test_get(self): bc = BucketCore(5); bc.set("k", 1); self.assertEqual(bc.get("k"), 1)
    def test_get_default(self): self.assertEqual(BucketCore(5).get("x", 5), 5)
    def test_invalidate(self): bc = BucketCore(5); bc.set("a", 1); self.assertTrue(bc.invalidate("a")); self.assertFalse(bc.invalidate("a"))
    def test_clear(self): bc = BucketCore(5); bc.set("a", 1); bc.set("b", 2); self.assertEqual(bc.clear(), 2); self.assertEqual(len(bc), 0)
    def test_len(self): bc = BucketCore(5); bc.set("a", 1); bc.set("b", 2); self.assertEqual(len(bc), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): BucketCore(0)
    def test_deterministic(self): bc = BucketCore(5); bc.set("a", 1); self.assertEqual(bc.get("a"), bc.get("a"))
    def test_many(self): bc = BucketCore(10); [bc.set(f"k{i}", i) for i in range(10)]; self.assertTrue(bc.full())
