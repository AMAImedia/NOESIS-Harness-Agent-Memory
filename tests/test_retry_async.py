import unittest
from noesis_harness.retry_async import retry_sync, retry_with_log

class TestRetryAsync(unittest.TestCase):
    def test_ok(self): self.assertEqual(retry_sync(lambda: 1, max_attempts=3, delay=0), 1)
    def test_fail_then_ok(self):
        c = [0]
        def fn(): c[0] += 1; return "ok" if c[0] >= 3 else (_ for _ in ()).throw(ValueError("no"))
        self.assertEqual(retry_sync(fn, max_attempts=5, delay=0), "ok")
    def test_all_fail(self):
        with self.assertRaises(ValueError): retry_sync(lambda: (_ for _ in ()).throw(ValueError("x")), max_attempts=2, delay=0)
    def test_with_log(self):
        log = []
        def fn(): return 42
        self.assertEqual(retry_with_log(fn, log_fn=log.append), 42)
    def test_log_on_fail(self):
        log = []
        c = [0]
        def fn(): c[0] += 1; return "ok" if c[0] >= 2 else (_ for _ in ()).throw(ValueError("no"))
        retry_with_log(fn, max_attempts=3, delay=0, log_fn=log.append)
        self.assertEqual(len(log), 1)
    def test_deterministic(self): self.assertEqual(retry_sync(lambda: 42, delay=0), retry_sync(lambda: 42, delay=0))
    def test_single(self): self.assertEqual(retry_sync(lambda: "a", max_attempts=1, delay=0), "a")
    def test_many(self):
        for i in range(5): self.assertEqual(retry_sync(lambda: i, delay=0), i)
    def test_no_crash(self): retry_sync(lambda: None, max_attempts=2, delay=0)
    def test_custom_exception(self):
        class MyError(Exception): pass
        with self.assertRaises(MyError): retry_sync(lambda: (_ for _ in ()).throw(MyError()), delay=0)
