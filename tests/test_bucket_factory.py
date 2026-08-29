import unittest
from noesis_harness.bucket_factory import BucketFactory

class TestBucketFactory(unittest.TestCase):
    def test_get(self): bf = BucketFactory(5, lambda k: k * 2); self.assertEqual(bf.get("a"), "aa")
    def test_missing(self): self.assertIsNone(BucketFactory(5).get("x"))
    def test_full(self): bf = BucketFactory(2, lambda k: k); bf.get("a"); bf.get("b"); self.assertTrue(bf.full()); self.assertIsNone(bf.get("c"))
    def test_invalidate(self): bf = BucketFactory(5, lambda k: k); bf.get("a"); self.assertTrue(bf.invalidate("a")); self.assertIsNone(bf.get("a"))
    def test_clear(self): bf = BucketFactory(5, lambda k: k); bf.get("a"); bf.get("b"); self.assertEqual(bf.clear(), 2); self.assertEqual(len(bf), 0)
    def test_len(self): bf = BucketFactory(5, lambda k: k); bf.get("a"); bf.get("b"); self.assertEqual(len(bf), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): BucketFactory(0)
    def test_deterministic(self): bf = BucketFactory(5, lambda k: 5); self.assertEqual(bf.get("a"), bf.get("a"))
    def test_many(self): bf = BucketFactory(10, lambda k: k); [bf.get(f"k{i}") for i in range(10)]; self.assertTrue(bf.full())
    def test_no_factory(self): self.assertIsNone(BucketFactory(5).get("x"))
