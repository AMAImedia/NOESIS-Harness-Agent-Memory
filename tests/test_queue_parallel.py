import threading, unittest
from noesis_harness.queue_parallel import QueueParallel

class TestQueueParallel(unittest.TestCase):
    def test_push_pop(self): q = QueueParallel(); q.push(1); q.push(2); self.assertEqual(q.pop(), 1)
    def test_empty(self): q = QueueParallel(); self.assertIsNone(q.pop()); self.assertTrue(q.empty())
    def test_cap(self): q = QueueParallel(2); q.push(1); q.push(2); self.assertTrue(q.full()); self.assertFalse(q.push(3))
    def test_peek(self): q = QueueParallel(); q.push(1); self.assertEqual(q.peek(), 1); self.assertEqual(len(q), 1)
    def test_len(self): q = QueueParallel(); q.push(1); q.push(2); self.assertEqual(len(q), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): QueueParallel(-1)
    def test_thread_safe(self):
        q = QueueParallel(); pushed = [0]
        def worker():
            for _ in range(100): q.push(1); pushed[0] += 1
        threads = [threading.Thread(target=worker) for _ in range(3)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(pushed[0], 300)
    def test_deterministic(self): q = QueueParallel(); q.push(1); self.assertEqual(q.peek(), 1)
    def test_many(self): q = QueueParallel(); [q.push(i) for i in range(5)]; self.assertEqual(len(q), 5)
    def test_no_crash(self): q = QueueParallel(1); q.push(1); q.pop(); q.push(2)
