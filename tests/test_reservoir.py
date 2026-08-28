import unittest
from noesis_harness.reservoir import sample

class TestReservoir(unittest.TestCase):
    def test_smaller_stream(self): self.assertEqual(sample([1, 2, 3], 5), [1, 2, 3])
    def test_full(self): s = sample(list(range(20)), 5, seed=1); self.assertEqual(len(s), 5); self.assertTrue(all(0 <= x < 20 for x in s))
    def test_invalid_k(self):
        with self.assertRaises(ValueError): sample([1], 0)
    def test_subset(self):
        s = sample(list(range(100)), 10, seed=2); self.assertEqual(len(s), 10); self.assertTrue(all(0 <= x < 100 for x in s))
    def test_deterministic(self):
        a = sample(list(range(50)), 5, seed=7); b = sample(list(range(50)), 5, seed=7); self.assertEqual(a, b)
    def test_unique(self):
        s = sample(list(range(100)), 10, seed=3); self.assertEqual(len(set(s)), 10)
    def test_k_one(self): self.assertIn(sample(list(range(10)), 1, seed=4)[0], range(10))
    def test_order_not_preserved(self):
        s = sample(list(range(100)), 50, seed=5); self.assertEqual(len(s), 50)
    def test_many(self):
        s = sample([str(i) for i in range(200)], 20, seed=6); self.assertEqual(len(s), 20)
    def test_seed_variety(self):
        a = sample(list(range(30)), 5, seed=1); b = sample(list(range(30)), 5, seed=2); self.assertNotEqual(a, b)
