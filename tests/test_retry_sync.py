import unittest
from noesis_harness.retry_sync import retry, retry_until

class TestRetrySync(unittest.TestCase):
    def test_ok(self): self.assertEqual(retry(lambda: 1, max_attempts=3), 1)
    def test_fail_then_ok(self):
        c = [0]
        def fn(): c[0] += 1; return "ok" if c[0] >= 3 else (_ for _ in ()).throw(ValueError("no"))
        self.assertEqual(retry(fn, max_attempts=5), "ok")
    def test_all_fail(self):
        with self.assertRaises(ValueError): retry(lambda: (_ for _ in ()).throw(ValueError("x")), max_attempts=2)
    def test_retry_until(self): self.assertEqual(retry_until(lambda: 42, lambda x: x == 42), 42)
    def test_retry_until_fail(self):
        with self.assertRaises(RuntimeError): retry_until(lambda: 0, lambda x: x > 0, max_attempts=5)
    def test_deterministic(self): self.assertEqual(retry(lambda: 42), retry(lambda: 42))
    def test_single(self): self.assertEqual(retry(lambda: "a", max_attempts=1), "a")
    def test_many(self):
        for i in range(5): self.assertEqual(retry(lambda: i), i)
    def test_no_crash(self): retry(lambda: None, max_attempts=2)
    def test_custom_exception(self):
        class MyError(Exception): pass
        with self.assertRaises(MyError): retry(lambda: (_ for _ in ()).throw(MyError()))
