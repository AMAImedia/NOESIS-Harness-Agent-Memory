import unittest
from noesis_harness.rng import make, randint, choice, shuffle

class TestRNG(unittest.TestCase):
    def test_make(self): self.assertTrue(hasattr(make(1), "random"))
    def test_deterministic(self):
        a = make(7); b = make(7); self.assertEqual(randint(a, 0, 100), randint(b, 0, 100))
    def test_range(self):
        r = make(3)
        for _ in range(50): v = randint(r, 1, 6); self.assertIn(v, range(1, 7))
    def test_choice(self): r = make(2); self.assertIn(choice(r, [1, 2, 3]), [1, 2, 3])
    def test_shuffle(self):
        r = make(5); s = shuffle(r, [1, 2, 3, 4, 5]); self.assertEqual(sorted(s), [1, 2, 3, 4, 5])
    def test_shuffle_deterministic(self):
        a = make(9); b = make(9); self.assertEqual(shuffle(a, list(range(10))), shuffle(b, list(range(10))))
    def test_choice_deterministic(self):
        a = make(4); b = make(4); self.assertEqual(choice(a, [10, 20, 30]), choice(b, [10, 20, 30]))
    def test_distinct_seeds(self):
        a = make(1); b = make(2)
        seq_a = [randint(a, 0, 1_000_000) for _ in range(20)]
        seq_b = [randint(b, 0, 1_000_000) for _ in range(20)]
        self.assertNotEqual(seq_a, seq_b)
    def test_many(self):
        r = make(11)
        for _ in range(20): randint(r, 0, 100)
    def test_shuffle_no_mutate(self): r = make(8); orig = [1, 2, 3]; shuffle(r, orig); self.assertEqual(orig, [1, 2, 3])
