import unittest
from noesis_harness.queue_core import QueueCore

class TestQueueCore(unittest.TestCase):
    def test_core(self): qc = QueueCore(5); self.assertEqual(qc.core("a", 1), 1)
    def test_existing(self): qc = QueueCore(5); qc.core("a", 1); self.assertEqual(qc.core("a", 2), 2)
    def test_overflow(self): qc = QueueCore(2); qc.core("a", 1); qc.core("b", 2); qc.core("c", 3); self.assertEqual(len(qc), 2); self.assertIsNotNone(qc.get("c"))
    def test_get(self): qc = QueueCore(5); qc.set("k", 1); self.assertEqual(qc.get("k"), 1)
    def test_get_default(self): self.assertEqual(QueueCore(5).get("x", 5), 5)
    def test_invalidate(self): qc = QueueCore(5); qc.set("a", 1); self.assertTrue(qc.invalidate("a")); self.assertIsNone(qc.get("a"))
    def test_clear(self): qc = QueueCore(5); qc.set("a", 1); qc.set("b", 2); self.assertEqual(qc.clear(), 2); self.assertEqual(len(qc), 0)
    def test_len(self): qc = QueueCore(5); qc.set("a", 1); qc.set("b", 2); self.assertEqual(len(qc), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): QueueCore(-1)
    def test_deterministic(self): qc = QueueCore(5); qc.set("a", 1); self.assertEqual(qc.get("a"), qc.get("a"))
    def test_many(self): qc = QueueCore(10); [qc.set(f"k{i}", i) for i in range(10)]; self.assertTrue(qc.full())
