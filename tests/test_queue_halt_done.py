import unittest
from noesis_harness.queue_halt_done import QueueHaltDone

class TestQueueHaltDone(unittest.TestCase):
    def test_halt_done(self): qh = QueueHaltDone(5); self.assertEqual(qh.halt_done("a", 1), 1)
    def test_existing(self): qh = QueueHaltDone(5); qh.halt_done("a", 1); self.assertEqual(qh.halt_done("a", 2), 2)
    def test_overflow(self): qh = QueueHaltDone(2); qh.halt_done("a", 1); qh.halt_done("b", 2); qh.halt_done("c", 3); self.assertEqual(len(qh), 2); self.assertIsNotNone(qh.get("c"))
    def test_get(self): qh = QueueHaltDone(5); qh.set("k", 1); self.assertEqual(qh.get("k"), 1)
    def test_get_default(self): self.assertEqual(QueueHaltDone(5).get("x", 5), 5)
    def test_invalidate(self): qh = QueueHaltDone(5); qh.set("a", 1); self.assertTrue(qh.invalidate("a")); self.assertIsNone(qh.get("a"))
    def test_clear(self): qh = QueueHaltDone(5); qh.set("a", 1); qh.set("b", 2); self.assertEqual(qh.clear(), 2); self.assertEqual(len(qh), 0)
    def test_len(self): qh = QueueHaltDone(5); qh.set("a", 1); qh.set("b", 2); self.assertEqual(len(qh), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): QueueHaltDone(-1)
    def test_deterministic(self): qh = QueueHaltDone(5); qh.set("a", 1); self.assertEqual(qh.get("a"), qh.get("a"))
    def test_many(self): qh = QueueHaltDone(10); [qh.set(f"k{i}", i) for i in range(10)]; self.assertTrue(qh.full())
