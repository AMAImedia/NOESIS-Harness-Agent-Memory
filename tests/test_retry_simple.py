import unittest
from noesis_harness.retry_simple import retry

class TestRetrySimple(unittest.TestCase):
    def test_ok(self): self.assertEqual(retry(lambda: 1, max_attempts=3), 1)
    def test_fail_then_ok(self):
        c = [0]
        def fn():
            c[0] += 1
            if c[0] < 3: raise ValueError("no")
            return "ok"
        self.assertEqual(retry(fn, max_attempts=5), "ok")
    def test_all_fail(self):
        with self.assertRaises(ValueError): retry(lambda: (_ for _ in ()).throw(ValueError("x")), max_attempts=2)
    def test_exception_type(self):
        with self.assertRaises(RuntimeError): retry(lambda: (_ for _ in ()).throw(RuntimeError("y")), max_attempts=1)
    def test_deterministic(self): self.assertEqual(retry(lambda: 42), retry(lambda: 42))
    def test_single(self): self.assertEqual(retry(lambda: "a", max_attempts=1), "a")
    def test_many(self):
        for i in range(5): self.assertEqual(retry(lambda: i), i)
    def test_no_crash(self): retry(lambda: None, max_attempts=2)
    def test_custom_exception(self):
        class MyError(Exception): pass
        with self.assertRaises(MyError): retry(lambda: (_ for _ in ()).throw(MyError()))
    def test_args(self): self.assertEqual(retry(lambda: 1 + 2), 3)
