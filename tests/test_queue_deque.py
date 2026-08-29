import threading, unittest
from noesis_harness.queue_deque import ThreadQueue

class TestQueueDeque(unittest.TestCase):
    def test_push_pop(self): q = ThreadQueue(); q.push(1); q.push(2); self.assertEqual(q.pop(), 1); self.assertEqual(q.pop(), 2)
    def test_empty(self): self.assertIsNone(ThreadQueue().pop())
    def test_peek(self): q = ThreadQueue(); q.push(1); self.assertEqual(q.peek(), 1); self.assertEqual(q.size(), 1)
    def test_size(self): q = ThreadQueue(); q.push(1); q.push(2); self.assertEqual(q.size(), 2)
    def test_to_list(self): q = ThreadQueue(); q.push(1); q.push(2); self.assertEqual(q.to_list(), [1, 2])
    def test_maxlen(self): q = ThreadQueue(maxlen=2); q.push(1); q.push(2); q.push(3); self.assertEqual(q.to_list(), [2, 3])
    def test_thread_safety(self):
        q = ThreadQueue()
        def producer():
            for i in range(100): q.push(i)
        def consumer():
            for _ in range(100): q.pop()
        threads = [threading.Thread(target=producer) for _ in range(3)]
        threads += [threading.Thread(target=consumer) for _ in range(3)]
        for t in threads: t.start()
        for t in threads: t.join()
    def test_deterministic(self): q = ThreadQueue(); q.push(1); self.assertEqual(q.peek(), q.peek())
    def test_many(self): q = ThreadQueue(); [q.push(i) for i in range(10)]; self.assertEqual(q.size(), 10)
    def test_no_crash(self): q = ThreadQueue(); q.push(None); self.assertIsNone(q.pop())
