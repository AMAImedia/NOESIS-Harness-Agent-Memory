"""Tests for noesis_harness.lease_clock.

Verifies that the lease TTL clock helper is pure, deterministic given input,
and correctly reports remaining time and expiry for active, lapsed, and
malformed leases.
"""

import unittest

from noesis_harness import lease_clock


class TestLeaseClock(unittest.TestCase):

    def test_remaining_positive(self):
        lease = {"expires_at": 1000.0}
        self.assertAlmostEqual(lease_clock.remaining(lease, now=900.0), 100.0)

    def test_remaining_expired_clamped_at_zero(self):
        lease = {"expires_at": 1000.0}
        self.assertEqual(lease_clock.remaining(lease, now=1500.0), 0.0)

    def test_remaining_far_in_past_clamped_at_zero(self):
        lease = {"expires_at": 100.0}
        self.assertEqual(lease_clock.remaining(lease, now=99999.0), 0.0)

    def test_is_expired_true_when_past(self):
        lease = {"expires_at": 1000.0}
        self.assertTrue(lease_clock.is_expired(lease, now=1001.0))

    def test_is_expired_false_when_active(self):
        lease = {"expires_at": 1000.0}
        self.assertFalse(lease_clock.is_expired(lease, now=999.0))

    def test_is_expired_true_when_equal(self):
        lease = {"expires_at": 1000.0}
        self.assertTrue(lease_clock.is_expired(lease, now=1000.0))

    def test_now_override_used(self):
        lease = {"expires_at": 2000.0}
        self.assertAlmostEqual(lease_clock.remaining(lease, now=1500.0), 500.0)
        self.assertFalse(lease_clock.is_expired(lease, now=1500.0))

    def test_boundary_exactly_at_expiry(self):
        lease = {"expires_at": 1234.0}
        self.assertEqual(lease_clock.remaining(lease, now=1234.0), 0.0)

    def test_missing_expires_at_field(self):
        lease = {"owner": "x"}
        self.assertEqual(lease_clock.remaining(lease), 0.0)
        self.assertTrue(lease_clock.is_expired(lease))

    def test_none_expires_at_field(self):
        lease = {"expires_at": None}
        self.assertEqual(lease_clock.remaining(lease, now=500.0), 0.0)
        self.assertTrue(lease_clock.is_expired(lease, now=500.0))

    def test_empty_lease_dict(self):
        self.assertEqual(lease_clock.remaining({}), 0.0)
        self.assertTrue(lease_clock.is_expired({}))

    def test_deterministic(self):
        lease = {"expires_at": 5000.0}
        a = lease_clock.remaining(lease, now=4000.0)
        b = lease_clock.remaining(lease, now=4000.0)
        self.assertEqual(a, b)
        self.assertEqual(
            lease_clock.is_expired(lease, now=4000.0),
            lease_clock.is_expired(lease, now=4000.0),
        )

    def test_future_lease_not_expired_with_default_now(self):
        future = {"expires_at": 1 << 40}
        self.assertGreaterEqual(lease_clock.remaining(future), 0.0)
        self.assertFalse(lease_clock.is_expired(future))


if __name__ == "__main__":
    unittest.main()
