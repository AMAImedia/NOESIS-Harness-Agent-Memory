import unittest
from noesis_harness.batch_computed import BatchComputed

class TestBatchComputed(unittest.TestCase):
    def test_register_get(self): m = BatchComputed(); m.register("a", lambda: 1); m.register("b", lambda: 2); self.assertEqual(m.get_batch(["a", "b"]), {"a": 1, "b": 2})
    def test_cached(self): m = BatchComputed(); m.register("a", lambda: 1); m.get_batch(["a"]); self.assertEqual(m.get_batch(["a"]), {"a": 1})
    def test_missing(self): self.assertEqual(BatchComputed().get_batch(["x"]), {})
    def test_invalidate(self): m = BatchComputed(); m.register("a", lambda: 1); m.get_batch(["a"]); self.assertTrue(m.invalidate("a")); self.assertEqual(m.get_batch(["a"]), {})
    def test_clear(self): m = BatchComputed(); m.register("a", lambda: 1); m.get_batch(["a"]); self.assertEqual(m.clear(), 1); self.assertEqual(len(m), 0)
    def test_len(self): m = BatchComputed(); m.register("a", lambda: 1); m.register("b", lambda: 2); m.get_batch(["a", "b"]); self.assertEqual(len(m), 2)
    def test_deterministic(self): m = BatchComputed(); m.register("a", lambda: 5); self.assertEqual(m.get_batch(["a"]), {"a": 5})
    def test_many(self): m = BatchComputed(); [m.register(f"k{i}", lambda i=i: i) for i in range(5)]; self.assertEqual(m.get_batch([f"k{i}" for i in range(5)]), {f"k{i}": i for i in range(5)})
    def test_no_crash(self): BatchComputed().get_batch(["x"])
    def test_partial(self): m = BatchComputed(); m.register("a", lambda: 1); self.assertEqual(m.get_batch(["a", "missing"]), {"a": 1})
