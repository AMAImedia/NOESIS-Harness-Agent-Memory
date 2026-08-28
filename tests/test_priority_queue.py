import threading
import unittest
from noesis_harness.priority_queue import PriorityQueue

class TestPriorityQueue(unittest.TestCase):
    def test_pop_order(self):
        q = PriorityQueue()
        q.push("low", 10); q.push("high", 0); q.push("mid", 5)
        self.assertEqual(q.pop(), "high"); self.assertEqual(q.pop(), "mid"); self.assertEqual(q.pop(), "low")
    def test_tie_fifo(self):
        q = PriorityQueue(); q.push("a", 1); q.push("b", 1); q.push("c", 1)
        self.assertEqual([q.pop(), q.pop(), q.pop()], ["a", "b", "c"])
    def test_peek(self):
        q = PriorityQueue(); q.push("x", 2); q.push("y", 1)
        self.assertEqual(q.peek(), "y"); self.assertEqual(len(q), 2)
    def test_empty(self):
        q = PriorityQueue(); self.assertIsNone(q.pop()); self.assertIsNone(q.peek()); self.assertEqual(len(q), 0)
    def test_negative(self):
        q = PriorityQueue(); q.push("neg", -5); q.push("zero", 0); self.assertEqual(q.pop(), "neg")
    def test_len(self):
        q = PriorityQueue(); q.push(1, 0); q.push(2, 0); self.assertEqual(len(q), 2); q.pop(); self.assertEqual(len(q), 1)
    def test_determinism(self):
        a = PriorityQueue(); b = PriorityQueue()
        for v in [(1, 2), (2, 1), (3, 1)]: a.push(v[0], v[1]); b.push(v[0], v[1])
        self.assertEqual([a.pop(), a.pop(), a.pop()], [b.pop(), b.pop(), b.pop()])
    def test_thread_smoke(self):
        q = PriorityQueue(); threads = []
        def push_many():
            for i in range(20): q.push(i, i % 3)
        for _ in range(4): t = threading.Thread(target=push_many); threads.append(t); t.start()
        for t in threads: t.join()
        self.assertEqual(len(q), 80)
    def test_many_priorities(self):
        q = PriorityQueue()
        for p in [3, 1, 4, 1, 5]: q.push(p, p)
        vals = []
        while len(q): vals.append(q.pop())
        self.assertEqual(vals, sorted(vals))
    def test_unique_counter(self):
        q = PriorityQueue(); q.push("a", 0); q.push("b", 0); q.push("c", 0)
        self.assertEqual(q.pop(), "a")
