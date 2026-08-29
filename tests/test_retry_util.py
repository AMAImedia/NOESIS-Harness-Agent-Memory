import unittest
from noesis_harness.retry_util import retry

class TestRetry(unittest.TestCase):
    def test_ok(self): self.assertEqual(retry(lambda: 1, max_attempts=3, delay=0), 1)
    def test_fail_then_ok(self):
        c = [0]
        def fn():
            c[0] += 1
            if c[0] < 3: raise ValueError("no")
            return "ok"
        self.assertEqual(retry(fn, max_attempts=5, delay=0), "ok")
    def test_all_fail(self):
        with self.assertRaises(ValueError): retry(lambda: (_ for _ in ()).throw(ValueError("x")), max_attempts=2, delay=0)
    def test_exception_type(self):
        with self.assertRaises(RuntimeError): retry(lambda: (_ for _ in ()).throw(RuntimeError("y")), max_attempts=1, delay=0)
    def test_deterministic(self): self.assertEqual(retry(lambda: 42, delay=0), retry(lambda: 42, delay=0))
    def test_single(self): self.assertEqual(retry(lambda: "a", max_attempts=1, delay=0), "a")
    def test_backoff(self):
        import time
        c = [0]
        def fn():
            c[0] += 1
            if c[0] < 3: raise ValueError("x")
            return "ok"
        s = time.perf_counter(); retry(fn, max_attempts=5, delay=0.01, backoff=2.0)
        self.assertGreater(time.perf_counter() - s, 0)
    def test_many(self):
        for i in range(5): self.assertEqual(retry(lambda: i, delay=0), i)
    def test_no_crash(self): retry(lambda: None, max_attempts=2, delay=0)
    def test_custom_exception(self):
        class MyError(Exception): pass
        with self.assertRaises(MyError): retry(lambda: (_ for _ in ()).throw(MyError()), delay=0)
