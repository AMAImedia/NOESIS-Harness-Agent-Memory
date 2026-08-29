import unittest
from noesis_harness.bucket_quit import BucketQuit

class TestBucketQuit(unittest.TestCase):
    def test_quit(self): bq = BucketQuit(5); self.assertEqual(bq.quit("a", 1), 1)
    def test_existing(self): bq = BucketQuit(5); bq.quit("a", 1); self.assertEqual(bq.quit("a", 2), 2)
    def test_full(self): bq = BucketQuit(2); bq.quit("a", 1); bq.quit("b", 2); self.assertTrue(bq.full()); self.assertIsNone(bq.quit("c", 3))
    def test_get(self): bq = BucketQuit(5); bq.set("k", 1); self.assertEqual(bq.get("k"), 1)
    def test_get_default(self): self.assertEqual(BucketQuit(5).get("x", 5), 5)
    def test_invalidate(self): bq = BucketQuit(5); bq.set("a", 1); self.assertTrue(bq.invalidate("a")); self.assertFalse(bq.invalidate("a"))
    def test_clear(self): bq = BucketQuit(5); bq.set("a", 1); bq.set("b", 2); self.assertEqual(bq.clear(), 2); self.assertEqual(len(bq), 0)
    def test_len(self): bq = BucketQuit(5); bq.set("a", 1); bq.set("b", 2); self.assertEqual(len(bq), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): BucketQuit(0)
    def test_deterministic(self): bq = BucketQuit(5); bq.set("a", 1); self.assertEqual(bq.get("a"), bq.get("a"))
    def test_many(self): bq = BucketQuit(10); [bq.set(f"k{i}", i) for i in range(10)]; self.assertTrue(bq.full())
