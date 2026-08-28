import unittest
from noesis_harness.log_buffer import LogBuffer

class TestLogBuffer(unittest.TestCase):
    def test_log(self): b = LogBuffer(10); b.log("info", "hi"); self.assertEqual(b.entries(), [("info", "hi")])
    def test_capacity(self): b = LogBuffer(2); b.log("a", "1"); b.log("a", "2"); b.log("a", "3"); self.assertEqual(len(b), 2); self.assertEqual(b.entries()[0][1], "2")
    def test_filter(self): b = LogBuffer(10); b.log("info", "a"); b.log("error", "b"); self.assertEqual(b.entries("info"), [("info", "a")])
    def test_clear(self): b = LogBuffer(10); b.log("a", "x"); b.clear(); self.assertEqual(len(b), 0)
    def test_len(self): b = LogBuffer(10); b.log("a", "1"); b.log("b", "2"); self.assertEqual(len(b), 2)
    def test_empty(self): self.assertEqual(LogBuffer(10).entries(), [])
    def test_levels(self): b = LogBuffer(10); b.log("debug", "d"); b.log("info", "i"); self.assertEqual(len(b.entries()), 2)
    def test_many(self):
        b = LogBuffer(5)
        for i in range(10): b.log("info", str(i))
        self.assertEqual(len(b), 5); self.assertEqual(b.entries()[-1][1], "9")
    def test_determinism(self):
        a = LogBuffer(10); b = LogBuffer(10)
        a.log("x", "1"); b.log("x", "1"); self.assertEqual(a.entries(), b.entries())
    def test_thread(self):
        import threading
        b = LogBuffer(100)
        def add(): [b.log("info", str(i)) for i in range(20)]
        ts = [threading.Thread(target=add) for _ in range(3)]
        [t.start() for t in ts]; [t.join() for t in ts]; self.assertLessEqual(len(b), 100)
