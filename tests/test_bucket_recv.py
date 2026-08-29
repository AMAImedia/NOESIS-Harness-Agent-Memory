import unittest
from noesis_harness.bucket_recv import BucketRecv

class TestBucketRecv(unittest.TestCase):
    def test_recv(self): br = BucketRecv(5); self.assertEqual(br.recv("a", 1), 1)
    def test_existing(self): br = BucketRecv(5); br.recv("a", 1); self.assertEqual(br.recv("a", 2), 2)
    def test_full(self): br = BucketRecv(2); br.recv("a", 1); br.recv("b", 2); self.assertTrue(br.full()); self.assertIsNone(br.recv("c", 3))
    def test_get(self): br = BucketRecv(5); br.set("k", 1); self.assertEqual(br.get("k"), 1)
    def test_get_default(self): self.assertEqual(BucketRecv(5).get("x", 5), 5)
    def test_invalidate(self): br = BucketRecv(5); br.set("a", 1); self.assertTrue(br.invalidate("a")); self.assertFalse(br.invalidate("a"))
    def test_clear(self): br = BucketRecv(5); br.set("a", 1); br.set("b", 2); self.assertEqual(br.clear(), 2); self.assertEqual(len(br), 0)
    def test_len(self): br = BucketRecv(5); br.set("a", 1); br.set("b", 2); self.assertEqual(len(br), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): BucketRecv(0)
    def test_deterministic(self): br = BucketRecv(5); br.set("a", 1); self.assertEqual(br.get("a"), br.get("a"))
    def test_many(self): br = BucketRecv(10); [br.set(f"k{i}", i) for i in range(10)]; self.assertTrue(br.full())
