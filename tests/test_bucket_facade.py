import unittest
from noesis_harness.bucket_facade import BucketFacade

class TestBucketFacade(unittest.TestCase):
    def test_cache(self): bf = BucketFacade(5); self.assertEqual(bf.cache("a", 1), 1)
    def test_existing(self): bf = BucketFacade(5); bf.cache("a", 1); self.assertEqual(bf.cache("a", 2), 2)
    def test_full(self): bf = BucketFacade(2); bf.cache("a", 1); bf.cache("b", 2); self.assertTrue(bf.full()); self.assertIsNone(bf.cache("c", 3))
    def test_get(self): bf = BucketFacade(5); bf.set("k", 1); self.assertEqual(bf.get("k"), 1)
    def test_get_default(self): self.assertEqual(BucketFacade(5).get("x", 5), 5)
    def test_invalidate(self): bf = BucketFacade(5); bf.set("a", 1); self.assertTrue(bf.invalidate("a")); self.assertFalse(bf.invalidate("a"))
    def test_clear(self): bf = BucketFacade(5); bf.set("a", 1); bf.set("b", 2); self.assertEqual(bf.clear(), 2); self.assertEqual(len(bf), 0)
    def test_len(self): bf = BucketFacade(5); bf.set("a", 1); bf.set("b", 2); self.assertEqual(len(bf), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): BucketFacade(0)
    def test_deterministic(self): bf = BucketFacade(5); bf.set("a", 1); self.assertEqual(bf.get("a"), bf.get("a"))
    def test_many(self): bf = BucketFacade(10); [bf.set(f"k{i}", i) for i in range(10)]; self.assertTrue(bf.full())
