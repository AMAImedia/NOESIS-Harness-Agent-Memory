import json, os, tempfile, unittest
from noesis_harness.queue_persist import FileQueue

class TestFileQueue(unittest.TestCase):
    def setUp(self): self.tmp = tempfile.mkdtemp(); self.path = os.path.join(self.tmp, "q.json")
    def test_push_pop(self): q = FileQueue(self.path); q.push(1); q.push(2); self.assertEqual(q.pop(), 1); self.assertEqual(q.pop(), 2)
    def test_peek(self): q = FileQueue(self.path); q.push(1); self.assertEqual(q.peek(), 1); self.assertEqual(len(q), 1)
    def test_empty_pop(self): self.assertIsNone(FileQueue(self.path).pop())
    def test_len(self): q = FileQueue(self.path); q.push(1); q.push(2); self.assertEqual(len(q), 2)
    def test_persistence(self): q = FileQueue(self.path); q.push(1); q2 = FileQueue(self.path); self.assertEqual(q2.pop(), 1)
    def test_order(self): q = FileQueue(self.path); q.push("a"); q.push("b"); self.assertEqual(q.pop(), "a")
    def test_empty_peek(self): self.assertIsNone(FileQueue(self.path).peek())
    def test_many(self):
        q = FileQueue(self.path)
        for i in range(10): q.push(i)
        self.assertEqual(len(q), 10)
    def test_determinism(self): q = FileQueue(self.path); q.push(1); self.assertEqual(q.peek(), 1)
    def test_pop_empty(self): q = FileQueue(self.path); self.assertIsNone(q.pop()); self.assertIsNone(q.pop())
