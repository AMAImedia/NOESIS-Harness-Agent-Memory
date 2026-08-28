import unittest
from noesis_harness.metrics_registry import MetricsRegistry

class TestMetricsRegistry(unittest.TestCase):
    def test_inc(self): m = MetricsRegistry(); self.assertEqual(m.inc("hits"), 1)
    def test_get(self): m = MetricsRegistry(); m.inc("hits", 3); self.assertEqual(m.get("hits"), 3)
    def test_zero(self): self.assertEqual(MetricsRegistry().get("x"), 0)
    def test_invalid(self):
        with self.assertRaises(ValueError): MetricsRegistry().inc("x", -1)
    def test_snapshot(self): m = MetricsRegistry(); m.inc("a"); m.inc("b"); self.assertEqual(m.snapshot(), {"a": 1, "b": 1})
    def test_no_mutation(self): m = MetricsRegistry(); m.inc("a"); m.snapshot(); self.assertEqual(m.get("a"), 1)
    def test_determinism(self): a = MetricsRegistry(); b = MetricsRegistry(); a.inc("x", 2); b.inc("x", 2); self.assertEqual(a.get("x"), b.get("x"))
    def test_many(self):
        m = MetricsRegistry()
        for i in range(5): m.inc(f"k{i}")
        self.assertEqual(len(m.snapshot()), 5)
    def test_cumulative(self):
        m = MetricsRegistry(); m.inc("a"); m.inc("a"); m.inc("a"); self.assertEqual(m.get("a"), 3)
    def test_by(self): m = MetricsRegistry(); self.assertEqual(m.inc("a", 5), 5)
