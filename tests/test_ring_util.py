import unittest
from noesis_harness.ring_util import RingBuf

class TestRingUtil(unittest.TestCase):
    def test_push(self): r = RingBuf(3); r.push(1); self.assertEqual(r.get(0), 1)
    def test_overflow(self): r = RingBuf(2); r.push(1); r.push(2); r.push(3); self.assertEqual(r.to_list(), [2, 3])
    def test_empty(self): self.assertEqual(len(RingBuf(3)), 0)
    def test_len(self): r = RingBuf(3); r.push(1); r.push(2); self.assertEqual(len(r), 2)
    def test_invalid_size(self):
        with self.assertRaises(ValueError): RingBuf(0)
    def test_out_of_range(self):
        r = RingBuf(3); r.push(1)
        with self.assertRaises(IndexError): r.get(1)
    def test_full(self): r = RingBuf(3); [r.push(i) for i in range(3)]; self.assertEqual(r.to_list(), [0, 1, 2])
    def test_deterministic(self): r = RingBuf(3); r.push(1); self.assertEqual(r.get(0), r.get(0))
    def test_many(self): r = RingBuf(5); [r.push(i) for i in range(10)]; self.assertEqual(r.to_list(), [5, 6, 7, 8, 9])
    def test_single(self): r = RingBuf(1); r.push(1); r.push(2); self.assertEqual(r.to_list(), [2])
