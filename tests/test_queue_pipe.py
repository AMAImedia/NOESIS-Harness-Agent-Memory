import unittest
from noesis_harness.queue_pipe import QueuePipe

class TestQueuePipe(unittest.TestCase):
    def test_pipe(self): qp = QueuePipe(5); self.assertEqual(qp.pipe("a", 1), 1)
    def test_existing(self): qp = QueuePipe(5); qp.pipe("a", 1); self.assertEqual(qp.pipe("a", 2), 2)
    def test_overflow(self): qp = QueuePipe(2); qp.pipe("a", 1); qp.pipe("b", 2); qp.pipe("c", 3); self.assertEqual(len(qp), 2); self.assertIsNotNone(qp.get("c"))
    def test_get(self): qp = QueuePipe(5); qp.set("k", 1); self.assertEqual(qp.get("k"), 1)
    def test_get_default(self): self.assertEqual(QueuePipe(5).get("x", 5), 5)
    def test_invalidate(self): qp = QueuePipe(5); qp.set("a", 1); self.assertTrue(qp.invalidate("a")); self.assertIsNone(qp.get("a"))
    def test_clear(self): qp = QueuePipe(5); qp.set("a", 1); qp.set("b", 2); self.assertEqual(qp.clear(), 2); self.assertEqual(len(qp), 0)
    def test_len(self): qp = QueuePipe(5); qp.set("a", 1); qp.set("b", 2); self.assertEqual(len(qp), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): QueuePipe(-1)
    def test_deterministic(self): qp = QueuePipe(5); qp.set("a", 1); self.assertEqual(qp.get("a"), qp.get("a"))
    def test_many(self): qp = QueuePipe(10); [qp.set(f"k{i}", i) for i in range(10)]; self.assertTrue(qp.full())
