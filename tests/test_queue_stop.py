import unittest
from noesis_harness.queue_stop import QueueStop

class TestQueueStop(unittest.TestCase):
    def test_stop(self): qs = QueueStop(5); self.assertEqual(qs.stop("a", 1), 1)
    def test_existing(self): qs = QueueStop(5); qs.stop("a", 1); self.assertEqual(qs.stop("a", 2), 2)
    def test_overflow(self): qs = QueueStop(2); qs.stop("a", 1); qs.stop("b", 2); qs.stop("c", 3); self.assertEqual(len(qs), 2); self.assertIsNotNone(qs.get("c"))
    def test_get(self): qs = QueueStop(5); qs.set("k", 1); self.assertEqual(qs.get("k"), 1)
    def test_get_default(self): self.assertEqual(QueueStop(5).get("x", 5), 5)
    def test_invalidate(self): qs = QueueStop(5); qs.set("a", 1); self.assertTrue(qs.invalidate("a")); self.assertIsNone(qs.get("a"))
    def test_clear(self): qs = QueueStop(5); qs.set("a", 1); qs.set("b", 2); self.assertEqual(qs.clear(), 2); self.assertEqual(len(qs), 0)
    def test_len(self): qs = QueueStop(5); qs.set("a", 1); qs.set("b", 2); self.assertEqual(len(qs), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): QueueStop(-1)
    def test_deterministic(self): qs = QueueStop(5); qs.set("a", 1); self.assertEqual(qs.get("a"), qs.get("a"))
    def test_many(self): qs = QueueStop(10); [qs.set(f"k{i}", i) for i in range(10)]; self.assertTrue(qs.full())
