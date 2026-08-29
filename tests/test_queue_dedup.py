import unittest
from noesis_harness.queue_dedup import QueueDedup

class TestQueueDedup(unittest.TestCase):
    def test_push_pop(self): q = QueueDedup(); q.push(1); q.push(2); self.assertEqual(q.pop(), 1)
    def test_duplicate(self): q = QueueDedup(); q.push(1); self.assertFalse(q.push(1))
    def test_after_pop(self): q = QueueDedup(); q.push(1); q.pop(); self.assertTrue(q.push(1))
    def test_cap(self): q = QueueDedup(2); q.push(1); q.push(2); self.assertTrue(q.full()); self.assertFalse(q.push(3))
    def test_empty(self): q = QueueDedup(); self.assertIsNone(q.pop()); self.assertTrue(q.empty())
    def test_contains(self): q = QueueDedup(); q.push(1); self.assertTrue(q.contains(1)); self.assertFalse(q.contains(2))
    def test_len(self): q = QueueDedup(); q.push(1); q.push(2); self.assertEqual(len(q), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): QueueDedup(-1)
    def test_deterministic(self): q = QueueDedup(); q.push(1); self.assertTrue(q.contains(1))
    def test_many(self): q = QueueDedup(); [q.push(i) for i in range(5)]; self.assertEqual(len(q), 5)
