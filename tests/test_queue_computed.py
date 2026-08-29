import unittest
from noesis_harness.queue_computed import QueueComputed

class TestQueueComputed(unittest.TestCase):
    def test_get(self): qc = QueueComputed(5, lambda k: k * 2); self.assertEqual(qc.get("a"), "aa")
    def test_missing(self): self.assertIsNone(QueueComputed(5).get("x"))
    def test_overflow(self): qc = QueueComputed(2, lambda k: k); qc.get("a"); qc.get("b"); qc.get("c"); self.assertEqual(len(qc), 2); self.assertIsNotNone(qc.get("c"))
    def test_invalidate(self): qc = QueueComputed(5, lambda k: k); qc.get("a"); self.assertTrue(qc.invalidate("a")); self.assertIsNone(qc.get("a"))
    def test_clear(self): qc = QueueComputed(5, lambda k: k); qc.get("a"); qc.get("b"); self.assertEqual(qc.clear(), 2); self.assertEqual(len(qc), 0)
    def test_len(self): qc = QueueComputed(5, lambda k: k); qc.get("a"); qc.get("b"); self.assertEqual(len(qc), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): QueueComputed(-1)
    def test_deterministic(self): qc = QueueComputed(5, lambda k: 5); self.assertEqual(qc.get("a"), qc.get("a"))
    def test_many(self): qc = QueueComputed(10, lambda k: k); [qc.get(f"k{i}") for i in range(10)]; self.assertTrue(qc.full())
    def test_no_compute(self): self.assertIsNone(QueueComputed(5).get("x"))
