import unittest
from noesis_harness.queue_ring import RingQueue

class TestRingQueue(unittest.TestCase):
    def test_push_pop(self): q = RingQueue(3); q.push(1); q.push(2); self.assertEqual(q.pop(), 1); self.assertEqual(q.pop(), 2)
    def test_empty(self): q = RingQueue(3); self.assertIsNone(q.pop()); self.assertTrue(q.empty())
    def test_full(self): q = RingQueue(2); q.push(1); q.push(2); self.assertTrue(q.full()); self.assertFalse(q.push(3))
    def test_peek(self): q = RingQueue(3); q.push(1); self.assertEqual(q.peek(), 1); self.assertEqual(len(q), 1)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingQueue(0)
    def test_len(self): q = RingQueue(3); q.push(1); q.push(2); self.assertEqual(len(q), 2)
    def test_deterministic(self): q = RingQueue(3); q.push(1); self.assertEqual(q.peek(), 1)
    def test_many(self): q = RingQueue(5); [q.push(i) for i in range(5)]; self.assertTrue(q.full())
    def test_no_crash(self): q = RingQueue(1); q.push(1); q.pop(); q.push(2)
    def test_cycle(self): q = RingQueue(2); q.push(1); q.push(2); q.pop(); q.push(3); self.assertEqual(q.pop(), 2); self.assertEqual(q.pop(), 3)
