import unittest
from noesis_harness.queue_hook import QueueHook

class TestQueueHook(unittest.TestCase):
    def test_hook(self): qh = QueueHook(5); self.assertEqual(qh.hook("a", 1), 1)
    def test_existing(self): qh = QueueHook(5); qh.hook("a", 1); self.assertEqual(qh.hook("a", 2), 2)
    def test_overflow(self): qh = QueueHook(2); qh.hook("a", 1); qh.hook("b", 2); qh.hook("c", 3); self.assertEqual(len(qh), 2); self.assertIsNotNone(qh.get("c"))
    def test_get(self): qh = QueueHook(5); qh.set("k", 1); self.assertEqual(qh.get("k"), 1)
    def test_get_default(self): self.assertEqual(QueueHook(5).get("x", 5), 5)
    def test_invalidate(self): qh = QueueHook(5); qh.set("a", 1); self.assertTrue(qh.invalidate("a")); self.assertIsNone(qh.get("a"))
    def test_clear(self): qh = QueueHook(5); qh.set("a", 1); qh.set("b", 2); self.assertEqual(qh.clear(), 2); self.assertEqual(len(qh), 0)
    def test_len(self): qh = QueueHook(5); qh.set("a", 1); qh.set("b", 2); self.assertEqual(len(qh), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): QueueHook(-1)
    def test_deterministic(self): qh = QueueHook(5); qh.set("a", 1); self.assertEqual(qh.get("a"), qh.get("a"))
    def test_many(self): qh = QueueHook(10); [qh.set(f"k{i}", i) for i in range(10)]; self.assertTrue(qh.full())
