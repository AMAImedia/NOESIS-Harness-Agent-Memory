import unittest
from noesis_harness.bucket_dedup import BucketDedup

class TestBucketDedup(unittest.TestCase):
    def test_add(self): b = BucketDedup(5); self.assertTrue(b.add(1))
    def test_duplicate(self): b = BucketDedup(5); b.add(1); self.assertFalse(b.add(1))
    def test_full(self): b = BucketDedup(2); b.add(1); b.add(2); self.assertTrue(b.full()); self.assertFalse(b.add(3))
    def test_contains(self): b = BucketDedup(5); b.add(1); self.assertTrue(b.contains(1)); self.assertFalse(b.contains(2))
    def test_empty(self): b = BucketDedup(3); self.assertTrue(b.empty())
    def test_len(self): b = BucketDedup(5); b.add(1); b.add(2); self.assertEqual(len(b), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): BucketDedup(0)
    def test_deterministic(self): b = BucketDedup(5); b.add(1); self.assertTrue(b.contains(1))
    def test_many(self): b = BucketDedup(10); [b.add(i) for i in range(10)]; self.assertTrue(b.full())
    def test_no_crash(self): b = BucketDedup(1); b.add(1); b.add(2)
