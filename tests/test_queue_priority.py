import unittest
from noesis_harness.queue_priority import PriorityQueue

class TestPriorityQueue(unittest.TestCase):
    def test_push_pop(self): q = PriorityQueue(); q.push("a", 2); q.push("b", 1); self.assertEqual(q.pop(), "b")
    def test_empty(self): q = PriorityQueue(); self.assertIsNone(q.pop()); self.assertTrue(q.empty())
    def test_peek(self): q = PriorityQueue(); q.push("a", 5); self.assertEqual(q.peek(), "a"); self.assertEqual(len(q), 1)
    def test_len(self): q = PriorityQueue(); q.push("a", 1); q.push("b", 2); self.assertEqual(len(q), 2)
    def test_deterministic(self): q = PriorityQueue(); q.push("a", 1); self.assertEqual(q.peek(), "a")
    def test_many(self): q = PriorityQueue(); [q.push(f"k{i}", i) for i in range(5)]; self.assertEqual(len(q), 5)
    def test_order(self): q = PriorityQueue(); q.push("c", 3); q.push("a", 1); q.push("b", 2); self.assertEqual(q.pop(), "a"); self.assertEqual(q.pop(), "b")
    def test_no_crash(self): q = PriorityQueue(); q.push("a", 1); q.pop(); q.push("b", 2)
    def test_same_priority(self): q = PriorityQueue(); q.push("a", 1); q.push("b", 1); self.assertEqual(q.pop(), "a")
    def test_negative(self): q = PriorityQueue(); q.push("a", -1); q.push("b", 0); self.assertEqual(q.pop(), "a")
