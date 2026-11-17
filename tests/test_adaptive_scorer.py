import unittest
from noesis_harness.adaptive_scorer import AdaptiveScorer

class TestAdaptiveScorer(unittest.TestCase):
    def test_initial(self):
        s = AdaptiveScorer(); self.assertAlmostEqual(s.score(1.0, 0.0), 0.5)
    def test_learns_success(self):
        s = AdaptiveScorer(lr=0.5)
        for _ in range(20): s.update(1.0, 0.0, "success")
        w_s, w_r = s.weights(); self.assertGreater(w_s, w_r)
    def test_learns_failure(self):
        s = AdaptiveScorer(lr=0.5)
        for _ in range(20): s.update(1.0, 0.0, "failure")
        w_s, w_r = s.weights(); self.assertLess(w_s, 0.9)
    def test_partial(self):
        s = AdaptiveScorer(); s.update(0.5, 0.5, "partial"); self.assertEqual(s.count(), 1)
    def test_normalized(self):
        s = AdaptiveScorer(); s.update(1.0, 1.0, "success"); w_s, w_r = s.weights(); self.assertAlmostEqual(w_s + w_r, 1.0)
    def test_invalid_lr(self):
        with self.assertRaises(ValueError): AdaptiveScorer(lr=0)
    def test_clamped(self):
        s = AdaptiveScorer(); self.assertEqual(s.score(2.0, -1.0), 0.5)
    def test_deterministic(self):
        a = AdaptiveScorer(); b = AdaptiveScorer()
        for _ in range(10): a.update(0.8, 0.2, "success"); b.update(0.8, 0.2, "success")
        self.assertEqual(a.weights(), b.weights())
    def test_many(self):
        s = AdaptiveScorer()
        for i in range(100): s.update(i / 100, 1 - i / 100, "success" if i % 2 == 0 else "failure")
        self.assertEqual(s.count(), 100)
