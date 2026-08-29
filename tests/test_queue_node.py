import unittest
from noesis_harness.queue_node import QueueNode

class TestQueueNode(unittest.TestCase):
    def test_node(self): qn = QueueNode(5); self.assertEqual(qn.node("a", 1), 1)
    def test_existing(self): qn = QueueNode(5); qn.node("a", 1); self.assertEqual(qn.node("a", 2), 2)
    def test_overflow(self): qn = QueueNode(2); qn.node("a", 1); qn.node("b", 2); qn.node("c", 3); self.assertEqual(len(qn), 2); self.assertIsNotNone(qn.get("c"))
    def test_get(self): qn = QueueNode(5); qn.set("k", 1); self.assertEqual(qn.get("k"), 1)
    def test_get_default(self): self.assertEqual(QueueNode(5).get("x", 5), 5)
    def test_invalidate(self): qn = QueueNode(5); qn.set("a", 1); self.assertTrue(qn.invalidate("a")); self.assertIsNone(qn.get("a"))
    def test_clear(self): qn = QueueNode(5); qn.set("a", 1); qn.set("b", 2); self.assertEqual(qn.clear(), 2); self.assertEqual(len(qn), 0)
    def test_len(self): qn = QueueNode(5); qn.set("a", 1); qn.set("b", 2); self.assertEqual(len(qn), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): QueueNode(-1)
    def test_deterministic(self): qn = QueueNode(5); qn.set("a", 1); self.assertEqual(qn.get("a"), qn.get("a"))
    def test_many(self): qn = QueueNode(10); [qn.set(f"k{i}", i) for i in range(10)]; self.assertTrue(qn.full())
