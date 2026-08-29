import unittest
from noesis_harness.queue_hold import QueueHold

class TestQueueHold(unittest.TestCase):
    def test_hold(self): qh = QueueHold(5); self.assertEqual(qh.hold("a", 1), 1)
    def test_existing(self): qh = QueueHold(5); qh.hold("a", 1); self.assertEqual(qh.hold("a", 2), 2)
    def test_overflow(self): qh = QueueHold(2); qh.hold("a", 1); qh.hold("b", 2); qh.hold("c", 3); self.assertEqual(len(qh), 2); self.assertIsNotNone(qh.get("c"))
    def test_get(self): qh = QueueHold(5); qh.set("k", 1); self.assertEqual(qh.get("k"), 1)
    def test_get_default(self): self.assertEqual(QueueHold(5).get("x", 5), 5)
    def test_invalidate(self): qh = QueueHold(5); qh.set("a", 1); self.assertTrue(qh.invalidate("a")); self.assertIsNone(qh.get("a"))
    def test_clear(self): qh = QueueHold(5); qh.set("a", 1); qh.set("b", 2); self.assertEqual(qh.clear(), 2); self.assertEqual(len(qh), 0)
    def test_len(self): qh = QueueHold(5); qh.set("a", 1); qh.set("b", 2); self.assertEqual(len(qh), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): QueueHold(-1)
    def test_deterministic(self): qh = QueueHold(5); qh.set("a", 1); self.assertEqual(qh.get("a"), qh.get("a"))
    def test_many(self): qh = QueueHold(10); [qh.set(f"k{i}", i) for i in range(10)]; self.assertTrue(qh.full())
