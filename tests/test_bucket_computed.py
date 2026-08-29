import unittest
from noesis_harness.bucket_computed import BucketComputed

class TestBucketComputed(unittest.TestCase):
    def test_get(self): bc = BucketComputed(5, lambda k: k * 2); self.assertEqual(bc.get("a"), "aa")
    def test_missing(self): self.assertIsNone(BucketComputed(5).get("x"))
    def test_full(self): bc = BucketComputed(2, lambda k: k); bc.get("a"); bc.get("b"); self.assertTrue(bc.full()); self.assertIsNone(bc.get("c"))
    def test_invalidate(self): bc = BucketComputed(5, lambda k: k); bc.get("a"); self.assertTrue(bc.invalidate("a")); self.assertIsNone(bc.get("a"))
    def test_clear(self): bc = BucketComputed(5, lambda k: k); bc.get("a"); bc.get("b"); self.assertEqual(bc.clear(), 2); self.assertEqual(len(bc), 0)
    def test_len(self): bc = BucketComputed(5, lambda k: k); bc.get("a"); bc.get("b"); self.assertEqual(len(bc), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): BucketComputed(0)
    def test_deterministic(self): bc = BucketComputed(5, lambda k: 5); self.assertEqual(bc.get("a"), bc.get("a"))
    def test_many(self): bc = BucketComputed(10, lambda k: k); [bc.get(f"k{i}") for i in range(10)]; self.assertTrue(bc.full())
    def test_no_compute(self): self.assertIsNone(BucketComputed(5).get("x"))
