import unittest
from noesis_harness.batch_retry import batch_retry

class TestBatchRetry(unittest.TestCase):
    def test_all_ok(self): self.assertEqual(batch_retry([lambda: 1, lambda: 2]), [1, 2])
    def test_fail_then_ok(self):
        c = [0]
        def fn():
            c[0] += 1
            if c[0] < 2: raise ValueError("x")
            return "ok"
        self.assertEqual(batch_retry([fn, lambda: 1], max_attempts=3), ["ok", 1])
    def test_all_fail(self): self.assertIsNone(batch_retry([lambda: (_ for _ in ()).throw(ValueError())], max_attempts=1)[0])
    def test_empty(self): self.assertEqual(batch_retry([]), [])
    def test_single(self): self.assertEqual(batch_retry([lambda: 42]), [42])
    def test_mixed(self):
        c = [0]
        def flaky():
            c[0] += 1
            if c[0] == 1: raise ValueError("x")
            return "ok"
        self.assertEqual(batch_retry([flaky, lambda: 5], max_attempts=2), ["ok", 5])
    def test_deterministic(self): self.assertEqual(batch_retry([lambda: 1]), [1])
    def test_many(self): self.assertEqual(batch_retry([lambda i=i: i for i in range(5)]), [0, 1, 2, 3, 4])
    def test_no_crash(self): batch_retry([lambda: None, lambda: None])
    def test_partial_fail(self): self.assertIsNone(batch_retry([lambda: (_ for _ in ()).throw(ValueError()), lambda: 1], max_attempts=1)[0])
