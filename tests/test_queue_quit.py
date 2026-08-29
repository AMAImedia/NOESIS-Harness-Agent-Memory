import unittest
from noesis_harness.queue_quit import QueueQuit

class TestQueueQuit(unittest.TestCase):
    def test_quit(self): qq = QueueQuit(5); self.assertEqual(qq.quit("a", 1), 1)
    def test_existing(self): qq = QueueQuit(5); qq.quit("a", 1); self.assertEqual(qq.quit("a", 2), 2)
    def test_overflow(self): qq = QueueQuit(2); qq.quit("a", 1); qq.quit("b", 2); qq.quit("c", 3); self.assertEqual(len(qq), 2); self.assertIsNotNone(qq.get("c"))
    def test_get(self): qq = QueueQuit(5); qq.set("k", 1); self.assertEqual(qq.get("k"), 1)
    def test_get_default(self): self.assertEqual(QueueQuit(5).get("x", 5), 5)
    def test_invalidate(self): qq = QueueQuit(5); qq.set("a", 1); self.assertTrue(qq.invalidate("a")); self.assertIsNone(qq.get("a"))
    def test_clear(self): qq = QueueQuit(5); qq.set("a", 1); qq.set("b", 2); self.assertEqual(qq.clear(), 2); self.assertEqual(len(qq), 0)
    def test_len(self): qq = QueueQuit(5); qq.set("a", 1); qq.set("b", 2); self.assertEqual(len(qq), 2)
    def test_invalid(self):
        with self.assertRaises(ValueError): QueueQuit(-1)
    def test_deterministic(self): qq = QueueQuit(5); qq.set("a", 1); self.assertEqual(qq.get("a"), qq.get("a"))
    def test_many(self): qq = QueueQuit(10); [qq.set(f"k{i}", i) for i in range(10)]; self.assertTrue(qq.full())
