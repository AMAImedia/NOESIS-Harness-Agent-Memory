import unittest
from noesis_harness.sampler import WeightedSampler

class TestSampler(unittest.TestCase):
    def test_sample(self): s = WeightedSampler(1); s.add("a", 1); self.assertEqual(s.sample(), "a")
    def test_empty(self):
        with self.assertRaises(ValueError): WeightedSampler().sample()
    def test_invalid_weight(self):
        with self.assertRaises(ValueError): WeightedSampler().add("a", 0)
    def test_determinism(self):
        a = WeightedSampler(7); b = WeightedSampler(7); a.add("x", 9); b.add("x", 9); self.assertEqual(a.sample(), b.sample())
    def test_distribution(self):
        s = WeightedSampler(3); s.add("a", 1); s.add("b", 1)
        counts = {"a": 0, "b": 0}
        for _ in range(200): counts[s.sample()] += 1
        self.assertTrue(counts["a"] > 0 and counts["b"] > 0)
    def test_len(self): s = WeightedSampler(); s.add("a", 1); s.add("b", 1); self.assertEqual(len(s), 2)
    def test_weights(self):
        s = WeightedSampler(2); s.add("a", 1); s.add("b", 9); self.assertEqual(s.sample(), "b")
    def test_many(self):
        s = WeightedSampler(5)
        for w in range(1, 6): s.add(f"k{w}", w)
        self.assertEqual(len(s), 5)
    def test_seed_variety(self): s = WeightedSampler(11); s.add("a", 1); s.add("b", 1); self.assertIn(s.sample(), {"a", "b"})
    def test_no_crash(self): s = WeightedSampler(4); s.add("a", 2); s.add("b", 3); [s.sample() for _ in range(50)]
    def test_single_item(self): s = WeightedSampler(9); s.add("only", 5); self.assertEqual(s.sample(), "only")
