import unittest
from noesis_harness.queue_halt import QueueHalt

class TestQueueHalt(unittest.TestCase):
    def test_halt(self): qh = QueueHalt(5); self.assertEqual(qh.halt("a", 1), 1)
    def test_existing(self): qh = QueueHalt(5); qh.halt("a", 1); self.assertEqual(qh.halt("a", 2), 2)
    def test_overflow(self): qh = QueueHalt(2); qh.halt("a", 1); qh.halt("b", 2); qh.halt("c", 3); self.assertEqual(len(qh), 2); self.assertIsNotNone(qh.get("c"))
    def test_get(self): qh = QueueHalt(5); qh.set("k", 1); self.assertEqual(qh.get("k"), 1)
    def test_get_default(self): self.assertEqual(QueueHalt(5).get("x", 5), 5)
    def test_invalidate(self): qh = QueueHalt(5); qh.set("a", 1); self.assertTrue(qh.invalidate("a")); self.assertIsNone(qh.get("a"))
    def test_clear(self): qh = QueueHalt(5); qh.set("a", 1); qh.set("b", 2); self.assertEqual(qh.clear(), 2); self.assertEqual(len(qh), 0)
    def test_len(self): qh = QueueHalt(5); qh.set("a", 1); qh.set("b", 2); self.assertEqual(len(qh), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): QueueHalt(-1)
    def test_deterministic(self): qh = QueueHalt(5); qh.set("a", 1); self.assertEqual(qh.get("a"), qh.get("a"))
    def test_many(self): qh = QueueHalt(10); [qh.set(f"k{i}", i) for i in range(10)]; self.assertTrue(qh.full())
