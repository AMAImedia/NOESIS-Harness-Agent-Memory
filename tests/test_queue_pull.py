import unittest
from noesis_harness.queue_pull import QueuePull

class TestQueuePull(unittest.TestCase):
    def test_pull(self): qp = QueuePull(5); self.assertEqual(qp.pull("a", 1), 1)
    def test_existing(self): qp = QueuePull(5); qp.pull("a", 1); self.assertEqual(qp.pull("a", 2), 2)
    def test_overflow(self): qp = QueuePull(2); qp.pull("a", 1); qp.pull("b", 2); qp.pull("c", 3); self.assertEqual(len(qp), 2); self.assertIsNotNone(qp.get("c"))
    def test_get(self): qp = QueuePull(5); qp.set("k", 1); self.assertEqual(qp.get("k"), 1)
    def test_get_default(self): self.assertEqual(QueuePull(5).get("x", 5), 5)
    def test_invalidate(self): qp = QueuePull(5); qp.set("a", 1); self.assertTrue(qp.invalidate("a")); self.assertIsNone(qp.get("a"))
    def test_clear(self): qp = QueuePull(5); qp.set("a", 1); qp.set("b", 2); self.assertEqual(qp.clear(), 2); self.assertEqual(len(qp), 0)
    def test_len(self): qp = QueuePull(5); qp.set("a", 1); qp.set("b", 2); self.assertEqual(len(qp), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): QueuePull(-1)
    def test_deterministic(self): qp = QueuePull(5); qp.set("a", 1); self.assertEqual(qp.get("a"), qp.get("a"))
    def test_many(self): qp = QueuePull(10); [qp.set(f"k{i}", i) for i in range(10)]; self.assertTrue(qp.full())
