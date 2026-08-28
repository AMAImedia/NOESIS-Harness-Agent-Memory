import unittest
from noesis_harness.deque import BoundedDeque

class TestDeque(unittest.TestCase):
    def test_append(self): d = BoundedDeque(3); d.append(1); d.append(2); self.assertEqual(d.to_list(), [1, 2])
    def test_maxlen(self): d = BoundedDeque(2); d.append(1); d.append(2); d.append(3); self.assertEqual(d.to_list(), [2, 3])
    def test_pop(self): d = BoundedDeque(3); d.append(1); d.append(2); self.assertEqual(d.pop(), 2)
    def test_popleft(self): d = BoundedDeque(3); d.append(1); d.append(2); self.assertEqual(d.popleft(), 1)
    def test_empty_pop(self): d = BoundedDeque(3); self.assertIsNone(d.pop()); self.assertIsNone(d.popleft())
    def test_appendleft(self): d = BoundedDeque(3); d.append(1); d.appendleft(0); self.assertEqual(d.to_list(), [0, 1])
    def test_len(self): d = BoundedDeque(5); d.append(1); self.assertEqual(len(d), 1)
    def test_unbounded(self): d = BoundedDeque(); d.append(1); d.append(2); self.assertEqual(len(d), 2)
    def test_determinism(self): a = BoundedDeque(2); b = BoundedDeque(2); a.append(1); a.append(2); b.append(1); b.append(2); self.assertEqual(a.to_list(), b.to_list())
    def test_many(self):
        d = BoundedDeque(3)
        for i in range(10): d.append(i)
        self.assertEqual(d.to_list(), [7, 8, 9])
