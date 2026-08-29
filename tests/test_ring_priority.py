import unittest
from noesis_harness.ring_priority import RingPriority

class TestRingPriority(unittest.TestCase):
    def test_push_pop(self): q = RingPriority(3); q.push("a", 2); q.push("b", 1); self.assertEqual(q.pop(), "b")
    def test_empty(self): q = RingPriority(3); self.assertIsNone(q.pop()); self.assertTrue(q.empty())
    def test_full(self): q = RingPriority(2); q.push("a", 1); q.push("b", 2); self.assertTrue(q.full()); self.assertFalse(q.push("c", 0))
    def test_peek(self): q = RingPriority(3); q.push("a", 5); self.assertEqual(q.peek(), "a"); self.assertEqual(len(q), 1)
    def test_invalid(self):
        with self.assertRaises(ValueError): RingPriority(0)
    def test_len(self): q = RingPriority(3); q.push("a", 1); q.push("b", 2); self.assertEqual(len(q), 2)
    def test_deterministic(self): q = RingPriority(3); q.push("a", 1); self.assertEqual(q.peek(), "a")
    def test_many(self): q = RingPriority(5); [q.push(f"k{i}", i) for i in range(5)]; self.assertTrue(q.full())
    def test_order(self): q = RingPriority(5); q.push("c", 3); q.push("a", 1); q.push("b", 2); self.assertEqual(q.pop(), "a"); self.assertEqual(q.pop(), "b")
    def test_no_crash(self): q = RingPriority(1); q.push("a", 1); q.pop(); q.push("b", 2)
