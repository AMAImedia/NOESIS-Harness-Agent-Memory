import unittest
from noesis_harness.queue_batch import QueueBatch

class TestQueueBatch(unittest.TestCase):
    def test_push_pop(self): q = QueueBatch(5); q.push_batch([1,2,3]); self.assertEqual(q.pop_batch(2), [1,2])
    def test_empty(self): q = QueueBatch(3); self.assertEqual(q.pop_batch(1), []); self.assertTrue(q.empty())
    def test_full(self): q = QueueBatch(2); q.push_batch([1,2]); self.assertTrue(q.full()); self.assertEqual(q.push_batch([3]), 0)
    def test_partial_push(self): q = QueueBatch(3); self.assertEqual(q.push_batch([1,2,3,4]), 3)
    def test_peek(self): q = QueueBatch(5); q.push_batch([1,2,3]); self.assertEqual(q.peek_batch(2), [1,2])
    def test_len(self): q = QueueBatch(5); q.push_batch([1,2]); self.assertEqual(len(q), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): QueueBatch(0)
    def test_deterministic(self): q = QueueBatch(5); q.push_batch([1]); self.assertEqual(len(q), 1)
    def test_many(self): q = QueueBatch(10); q.push_batch(list(range(10))); self.assertTrue(q.full())
    def test_no_crash(self): q = QueueBatch(1); q.push_batch([1]); q.pop_batch(1); q.push_batch([2])
