import unittest
from noesis_harness.queue_simple import QueueSimple

class TestQueueSimple(unittest.TestCase):
    def test_remember(self): qs = QueueSimple(5); self.assertEqual(qs.remember("a", 1), 1)
    def test_existing(self): qs = QueueSimple(5); qs.remember("a", 1); self.assertEqual(qs.remember("a", 2), 2)
    def test_overflow(self): qs = QueueSimple(2); qs.remember("a", 1); qs.remember("b", 2); qs.remember("c", 3); self.assertEqual(len(qs), 2); self.assertIsNotNone(qs.get("c"))
    def test_get(self): qs = QueueSimple(5); qs.set("k", 1); self.assertEqual(qs.get("k"), 1)
    def test_get_default(self): self.assertEqual(QueueSimple(5).get("x", 5), 5)
    def test_invalidate(self): qs = QueueSimple(5); qs.set("a", 1); self.assertTrue(qs.invalidate("a")); self.assertIsNone(qs.get("a"))
    def test_clear(self): qs = QueueSimple(5); qs.set("a", 1); qs.set("b", 2); self.assertEqual(qs.clear(), 2); self.assertEqual(len(qs), 0)
    def test_len(self): qs = QueueSimple(5); qs.set("a", 1); qs.set("b", 2); self.assertEqual(len(qs), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): QueueSimple(-1)
    def test_deterministic(self): qs = QueueSimple(5); qs.set("a", 1); self.assertEqual(qs.get("a"), qs.get("a"))
    def test_many(self): qs = QueueSimple(10); [qs.set(f"k{i}", i) for i in range(10)]; self.assertTrue(qs.full())
