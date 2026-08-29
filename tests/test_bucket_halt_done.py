import unittest
from noesis_harness.bucket_halt_done import BucketHaltDone

class TestBucketHaltDone(unittest.TestCase):
    def test_halt_done(self): bh = BucketHaltDone(5); self.assertEqual(bh.halt_done("a", 1), 1)
    def test_existing(self): bh = BucketHaltDone(5); bh.halt_done("a", 1); self.assertEqual(bh.halt_done("a", 2), 2)
    def test_full(self): bh = BucketHaltDone(2); bh.halt_done("a", 1); bh.halt_done("b", 2); self.assertTrue(bh.full()); self.assertIsNone(bh.halt_done("c", 3))
    def test_get(self): bh = BucketHaltDone(5); bh.set("k", 1); self.assertEqual(bh.get("k"), 1)
    def test_get_default(self): self.assertEqual(BucketHaltDone(5).get("x", 5), 5)
    def test_invalidate(self): bh = BucketHaltDone(5); bh.set("a", 1); self.assertTrue(bh.invalidate("a")); self.assertFalse(bh.invalidate("a"))
    def test_clear(self): bh = BucketHaltDone(5); bh.set("a", 1); bh.set("b", 2); self.assertEqual(bh.clear(), 2); self.assertEqual(len(bh), 0)
    def test_len(self): bh = BucketHaltDone(5); bh.set("a", 1); bh.set("b", 2); self.assertEqual(len(bh), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): BucketHaltDone(0)
    def test_deterministic(self): bh = BucketHaltDone(5); bh.set("a", 1); self.assertEqual(bh.get("a"), bh.get("a"))
    def test_many(self): bh = BucketHaltDone(10); [bh.set(f"k{i}", i) for i in range(10)]; self.assertTrue(bh.full())
