import unittest
from noesis_harness.queue_map import QueueMap

class TestQueueMap(unittest.TestCase):
    def test_mapping(self): qm = QueueMap(5); self.assertEqual(qm.mapping("a", 1), 1)
    def test_existing(self): qm = QueueMap(5); qm.mapping("a", 1); self.assertEqual(qm.mapping("a", 2), 2)
    def test_overflow(self): qm = QueueMap(2); qm.mapping("a", 1); qm.mapping("b", 2); qm.mapping("c", 3); self.assertEqual(len(qm), 2); self.assertIsNotNone(qm.get("c"))
    def test_get(self): qm = QueueMap(5); qm.set("k", 1); self.assertEqual(qm.get("k"), 1)
    def test_get_default(self): self.assertEqual(QueueMap(5).get("x", 5), 5)
    def test_invalidate(self): qm = QueueMap(5); qm.set("a", 1); self.assertTrue(qm.invalidate("a")); self.assertIsNone(qm.get("a"))
    def test_clear(self): qm = QueueMap(5); qm.set("a", 1); qm.set("b", 2); self.assertEqual(qm.clear(), 2); self.assertEqual(len(qm), 0)
    def test_len(self): qm = QueueMap(5); qm.set("a", 1); qm.set("b", 2); self.assertEqual(len(qm), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): QueueMap(-1)
    def test_deterministic(self): qm = QueueMap(5); qm.set("a", 1); self.assertEqual(qm.get("a"), qm.get("a"))
    def test_many(self): qm = QueueMap(10); [qm.set(f"k{i}", i) for i in range(10)]; self.assertTrue(qm.full())
