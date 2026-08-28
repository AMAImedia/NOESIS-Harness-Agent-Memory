import unittest
from noesis_harness.heap import MinHeap

class TestHeap(unittest.TestCase):
    def test_push_pop(self): h = MinHeap(); h.push(3); h.push(1); h.push(2); self.assertEqual(h.pop(), 1); self.assertEqual(h.pop(), 2); self.assertEqual(h.pop(), 3)
    def test_peek(self): h = MinHeap(); h.push(5); self.assertEqual(h.peek(), 5); self.assertEqual(len(h), 1)
    def test_empty_pop(self): self.assertIsNone(MinHeap().pop())
    def test_empty_peek(self): self.assertIsNone(MinHeap().peek())
    def test_len(self): h = MinHeap(); h.push(1); h.push(2); self.assertEqual(len(h), 2)
    def test_order(self): h = MinHeap(); [h.push(i) for i in range(5, 0, -1)]; self.assertEqual([h.pop() for _ in range(5)], [1, 2, 3, 4, 5])
    def test_determinism(self): a = MinHeap(); b = MinHeap(); a.push(2); a.push(1); b.push(2); b.push(1); self.assertEqual(a.peek(), b.peek())
    def test_strings(self): h = MinHeap(); h.push("b"); h.push("a"); self.assertEqual(h.pop(), "a")
    def test_many(self):
        h = MinHeap()
        for i in range(10): h.push(i)
        self.assertEqual(len(h), 10)
    def test_duplicates(self): h = MinHeap(); h.push(1); h.push(1); self.assertEqual(h.pop(), 1); self.assertEqual(h.pop(), 1)
