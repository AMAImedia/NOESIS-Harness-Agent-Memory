import unittest
from noesis_harness.async_retry import retry_thread, parallel_retry

class TestAsyncRetry(unittest.TestCase):
    def test_retry_ok(self): self.assertEqual(retry_thread(lambda: 1, max_attempts=3), 1)
    def test_retry_fail_then_ok(self):
        c = [0]
        def fn():
            c[0] += 1
            if c[0] < 3: raise ValueError("no")
            return "ok"
        self.assertEqual(retry_thread(fn, max_attempts=5), "ok")
    def test_retry_all_fail(self):
        with self.assertRaises(ValueError): retry_thread(lambda: (_ for _ in ()).throw(ValueError("x")), max_attempts=2)
    def test_parallel_retry(self): self.assertEqual(parallel_retry([lambda: 1, lambda: 2]), [1, 2])
    def test_parallel_empty(self): self.assertEqual(parallel_retry([]), [])
    def test_parallel_single(self): self.assertEqual(parallel_retry([lambda: 42]), [42])
    def test_deterministic(self): self.assertEqual(retry_thread(lambda: 5), retry_thread(lambda: 5))
    def test_many(self): self.assertEqual(parallel_retry([lambda i=i: i for i in range(5)]), [0, 1, 2, 3, 4])
    def test_no_crash(self): parallel_retry([lambda: None, lambda: None])
    def test_exception(self):
        with self.assertRaises(ValueError): parallel_retry([lambda: (_ for _ in ()).throw(ValueError("x"))])
