import unittest
from noesis_harness.bucket_batch import BucketBatch

class TestBucketBatch(unittest.TestCase):
    def test_add_take(self): b = BucketBatch(5); b.add_batch([1,2,3]); self.assertEqual(b.take_batch(2), [1,2])
    def test_empty(self): b = BucketBatch(3); self.assertEqual(b.take_batch(1), []); self.assertTrue(b.empty())
    def test_full(self): b = BucketBatch(2); b.add_batch([1,2]); self.assertTrue(b.full()); self.assertEqual(b.add_batch([3]), 0)
    def test_partial_add(self): b = BucketBatch(3); self.assertEqual(b.add_batch([1,2,3,4]), 3)
    def test_len(self): b = BucketBatch(5); b.add_batch([1,2]); self.assertEqual(len(b), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): BucketBatch(0)
    def test_deterministic(self): b = BucketBatch(5); b.add_batch([1]); self.assertEqual(len(b), 1)
    def test_many(self): b = BucketBatch(10); b.add_batch(list(range(10))); self.assertTrue(b.full())
    def test_no_crash(self): b = BucketBatch(1); b.add_batch([1]); b.take_batch(1); b.add_batch([2])
    def test_order(self): b = BucketBatch(5); b.add_batch([1,2,3]); self.assertEqual(b.take_batch(3), [1,2,3])
