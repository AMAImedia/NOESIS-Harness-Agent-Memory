import unittest
from noesis_harness.queue_proxy import QueueProxy

class TestQueueProxy(unittest.TestCase):
    def test_get_set(self): qp = QueueProxy(5); qp.set("k", 1); self.assertEqual(qp.get("k"), 1)
    def test_missing(self): self.assertIsNone(QueueProxy(5).get("x"))
    def test_default(self): self.assertEqual(QueueProxy(5).get("x", 5), 5)
    def test_overflow(self): qp = QueueProxy(2); qp.set("a", 1); qp.set("b", 2); qp.set("c", 3); self.assertEqual(len(qp), 2); self.assertIsNotNone(qp.get("c"))
    def test_invalidate(self): qp = QueueProxy(5); qp.set("a", 1); self.assertTrue(qp.invalidate("a")); self.assertIsNone(qp.get("a"))
    def test_clear(self): qp = QueueProxy(5); qp.set("a", 1); qp.set("b", 2); self.assertEqual(qp.clear(), 2); self.assertEqual(len(qp), 0)
    def test_len(self): qp = QueueProxy(5); qp.set("a", 1); qp.set("b", 2); self.assertEqual(len(qp), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): QueueProxy(-1)
    def test_deterministic(self): qp = QueueProxy(5); qp.set("a", 1); self.assertEqual(qp.get("a"), qp.get("a"))
    def test_many(self): qp = QueueProxy(10); [qp.set(f"k{i}", i) for i in range(10)]; self.assertTrue(qp.full())
