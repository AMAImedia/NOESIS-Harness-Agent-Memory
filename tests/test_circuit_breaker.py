import unittest
from noesis_harness.circuit_breaker import CircuitBreaker

class TestCB(unittest.TestCase):
    def test_closed_initially(self): self.assertEqual(CircuitBreaker(3, 10).state(0), "closed")
    def test_open_after_threshold(self):
        cb = CircuitBreaker(3, 10); cb.record_failure(0); cb.record_failure(0); cb.record_failure(0)
        self.assertEqual(cb.state(0), "open")
    def test_half_open_after_reset(self):
        cb = CircuitBreaker(2, 5); cb.record_failure(0); cb.record_failure(0)
        self.assertEqual(cb.state(6), "half-open")
    def test_close_on_success(self):
        cb = CircuitBreaker(2, 5); cb.record_failure(0); cb.record_failure(0)
        cb.record_success(6); self.assertEqual(cb.state(6), "closed")
    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker(2, 5); cb.record_failure(0); cb.record_failure(0); cb.record_failure(6)
        self.assertEqual(cb.state(6), "open")
    def test_boundary(self):
        cb = CircuitBreaker(2, 5); cb.record_failure(0); cb.record_failure(0); self.assertEqual(cb.state(5), "half-open")
    def test_per_instance(self):
        a = CircuitBreaker(2, 10); b = CircuitBreaker(2, 10); a.record_failure(0); a.record_failure(0)
        self.assertEqual(a.state(0), "open"); self.assertEqual(b.state(0), "closed")
    def test_determinism(self):
        a = CircuitBreaker(2, 5); b = CircuitBreaker(2, 5)
        for t in [0, 0, 6, 6]: a.record_failure(t); b.record_failure(t)
        self.assertEqual(a.state(6), b.state(6))
    def test_invalid(self):
        with self.assertRaises(ValueError): CircuitBreaker(0, 10)
    def test_success_resets(self):
        cb = CircuitBreaker(3, 10); cb.record_failure(0); cb.record_success(0)
        cb.record_failure(0); cb.record_failure(0); self.assertEqual(cb.state(0), "closed")
