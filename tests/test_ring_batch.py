import unittest
from noesis_harness.ring_batch import RingBatch

class TestRingBatch(unittest.TestCase):
    def test_add_take(self): r = RingBatch(5); r.add_batch([1,2,3]); self.assertEqual(r.take_batch(2), [1,2])
    def test_overflow(self): r = RingBatch(3); r.add_batch([1,2,3,4,5]); self.assertEqual(r.take_batch(3), [1,2,3])
    def test_empty(self): r = RingBatch(3); self.assertEqual(r.take_batch(1), []); self.assertTrue(r.empty())
    def test_full(self): r = RingBatch(2); r.add_batch([1,2]); self.assertTrue(r.full())
    def test_len(self): r = RingBatch(5); r.add_batch([1,2]); self.assertEqual(len(r), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingBatch(0)
    def test_deterministic(self): r = RingBatch(5); r.add_batch([1]); self.assertEqual(r.take_batch(1), [1])
    def test_many(self): r = RingBatch(5); r.add_batch(list(range(10))); self.assertEqual(len(r), 5)
    def test_no_crash(self): r = RingBatch(1); r.add_batch([1]); r.take_batch(1); r.add_batch([2])
    def test_cycle(self): r = RingBatch(2); r.add_batch([1,2]); r.take_batch(1); r.add_batch([3]); self.assertEqual(r.take_batch(2), [2,3])
