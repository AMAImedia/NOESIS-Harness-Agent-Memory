import unittest
from noesis_harness.bucket_token import Bucket

class TestBucket(unittest.TestCase):
    def test_add(self): b = Bucket(5); b.add(3); self.assertEqual(b.tokens(), 3)
    def test_take(self): b = Bucket(5); b.add(3); self.assertEqual(b.take(2), 2); self.assertEqual(b.tokens(), 1)
    def test_overflow(self): b = Bucket(3); added = b.add(5); self.assertEqual(added, 3)
    def test_underflow(self): b = Bucket(3); taken = b.take(5); self.assertEqual(taken, 0)
    def test_free(self): b = Bucket(5); b.add(2); self.assertEqual(b.free(), 3)
    def test_invalid(self):
        with self.assertRaises(ValueError): Bucket(0)
    def test_len(self): b = Bucket(5); b.add(3); self.assertEqual(len(b), 3)
    def test_deterministic(self): b = Bucket(5); b.add(1); self.assertEqual(b.tokens(), 1)
    def test_many(self): b = Bucket(10); [b.add(1) for _ in range(10)]; self.assertEqual(b.tokens(), 10)
    def test_no_crash(self): b = Bucket(1); b.add(1); b.take(1); b.add(1)
