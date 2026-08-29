import unittest
from noesis_harness.queue_factory import QueueFactory

class TestQueueFactory(unittest.TestCase):
    def test_get(self): qf = QueueFactory(5, lambda k: k * 2); self.assertEqual(qf.get("a"), "aa")
    def test_missing(self): self.assertIsNone(QueueFactory(5).get("x"))
    def test_overflow(self): qf = QueueFactory(2, lambda k: k); qf.get("a"); qf.get("b"); qf.get("c"); self.assertEqual(len(qf), 2); self.assertIsNotNone(qf.get("c"))
    def test_invalidate(self): qf = QueueFactory(5, lambda k: k); qf.get("a"); self.assertTrue(qf.invalidate("a")); self.assertIsNone(qf.get("a"))
    def test_clear(self): qf = QueueFactory(5, lambda k: k); qf.get("a"); qf.get("b"); self.assertEqual(qf.clear(), 2); self.assertEqual(len(qf), 0)
    def test_len(self): qf = QueueFactory(5, lambda k: k); qf.get("a"); qf.get("b"); self.assertEqual(len(qf), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): QueueFactory(-1)
    def test_deterministic(self): qf = QueueFactory(5, lambda k: 5); self.assertEqual(qf.get("a"), qf.get("a"))
    def test_many(self): qf = QueueFactory(10, lambda k: k); [qf.get(f"k{i}") for i in range(10)]; self.assertTrue(qf.full())
    def test_no_factory(self): self.assertIsNone(QueueFactory(5).get("x"))
