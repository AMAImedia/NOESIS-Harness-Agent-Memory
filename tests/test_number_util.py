import unittest
from noesis_harness.number_util import is_even, is_odd, clamp, lerp, is_prime

class TestNumberUtil(unittest.TestCase):
    def test_even(self): self.assertTrue(is_even(4)); self.assertFalse(is_even(3))
    def test_odd(self): self.assertTrue(is_odd(3)); self.assertFalse(is_odd(4))
    def test_clamp(self): self.assertEqual(clamp(5, 0, 10), 5)
    def test_clamp_low(self): self.assertEqual(clamp(-1, 0, 10), 0)
    def test_clamp_high(self): self.assertEqual(clamp(11, 0, 10), 10)
    def test_lerp(self): self.assertEqual(lerp(0, 10, 0.5), 5.0)
    def test_prime(self): self.assertTrue(is_prime(2)); self.assertTrue(is_prime(7)); self.assertFalse(is_prime(4))
    def test_not_prime(self): self.assertFalse(is_prime(1)); self.assertFalse(is_prime(0))
    def test_deterministic(self): self.assertEqual(is_prime(13), is_prime(13))
    def test_many_primes(self): self.assertEqual([n for n in range(20) if is_prime(n)], [2, 3, 5, 7, 11, 13, 17, 19])
