import unittest
from noesis_harness.bucket_node import BucketNode

class TestBucketNode(unittest.TestCase):
    def test_node(self): bn = BucketNode(5); self.assertEqual(bn.node("a", 1), 1)
    def test_existing(self): bn = BucketNode(5); bn.node("a", 1); self.assertEqual(bn.node("a", 2), 2)
    def test_full(self): bn = BucketNode(2); bn.node("a", 1); bn.node("b", 2); self.assertTrue(bn.full()); self.assertIsNone(bn.node("c", 3))
    def test_get(self): bn = BucketNode(5); bn.set("k", 1); self.assertEqual(bn.get("k"), 1)
    def test_get_default(self): self.assertEqual(BucketNode(5).get("x", 5), 5)
    def test_invalidate(self): bn = BucketNode(5); bn.set("a", 1); self.assertTrue(bn.invalidate("a")); self.assertFalse(bn.invalidate("a"))
    def test_clear(self): bn = BucketNode(5); bn.set("a", 1); bn.set("b", 2); self.assertEqual(bn.clear(), 2); self.assertEqual(len(bn), 0)
    def test_len(self): bn = BucketNode(5); bn.set("a", 1); bn.set("b", 2); self.assertEqual(len(bn), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): BucketNode(0)
    def test_deterministic(self): bn = BucketNode(5); bn.set("a", 1); self.assertEqual(bn.get("a"), bn.get("a"))
    def test_many(self): bn = BucketNode(10); [bn.set(f"k{i}", i) for i in range(10)]; self.assertTrue(bn.full())
