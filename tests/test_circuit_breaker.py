"""Tests for noesis_harness.circuit_breaker.

Covers the consecutive-failure breaker (threshold, cooldown, half-open
recovery, open-failure accounting, reset), the strictly forward recovery
ladder (ordering, exhaustion without wrap, predicate escalation, validation),
and the guarded combination (trip without escalation). All state transitions
use an injected ``now`` so the suite is fully deterministic. Stdlib only.
"""

import unittest

from noesis_harness.circuit_breaker import (
    MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES,
    CircuitBreaker,
    CircuitState,
    GuardedRecovery,
    RecoveryLadder,
)


class TestCircuitBreakerStates(unittest.TestCase):

    def test_closed_below_threshold(self):
        breaker = CircuitBreaker(threshold=3, cooldown=60.0)
        self.assertEqual(breaker.state(0.0), CircuitState.CLOSED)
        breaker.record(False, 0.0)
        breaker.record(False, 1.0)
        self.assertEqual(breaker.consecutive_failures(), 2)
        self.assertEqual(breaker.state(1.0), CircuitState.CLOSED)
        self.assertTrue(breaker.allow(1.0))

    def test_opens_at_threshold(self):
        breaker = CircuitBreaker(threshold=3, cooldown=60.0)
        breaker.record(False, 0.0)
        breaker.record(False, 0.0)
        self.assertEqual(breaker.record(False, 0.0), CircuitState.OPEN)
        self.assertEqual(breaker.state(0.0), CircuitState.OPEN)
        self.assertEqual(breaker.consecutive_failures(), 3)

    def test_allow_denies_when_open(self):
        breaker = CircuitBreaker(threshold=2, cooldown=30.0)
        breaker.record(False, 0.0)
        breaker.record(False, 0.0)
        self.assertFalse(breaker.allow(0.0))
        self.assertFalse(breaker.allow(29.999))
        self.assertEqual(breaker.state(10.0), CircuitState.OPEN)

    def test_half_open_after_cooldown(self):
        breaker = CircuitBreaker(threshold=2, cooldown=10.0)
        breaker.record(False, 0.0)
        breaker.record(False, 0.0)
        self.assertEqual(breaker.state(9.999), CircuitState.OPEN)
        self.assertEqual(breaker.state(10.0), CircuitState.HALF_OPEN)
        self.assertTrue(breaker.allow(10.0))

    def test_success_resets_failures(self):
        breaker = CircuitBreaker(threshold=3, cooldown=60.0)
        breaker.record(False, 0.0)
        breaker.record(False, 0.0)
        self.assertEqual(breaker.record(True, 1.0), CircuitState.CLOSED)
        self.assertEqual(breaker.consecutive_failures(), 0)
        self.assertEqual(breaker.state(1.0), CircuitState.CLOSED)
        self.assertTrue(breaker.allow(1.0))

    def test_half_open_failure_reopens_and_resets_cooldown(self):
        breaker = CircuitBreaker(threshold=2, cooldown=10.0)
        breaker.record(False, 0.0)
        breaker.record(False, 0.0)
        self.assertEqual(breaker.state(10.0), CircuitState.HALF_OPEN)
        self.assertEqual(breaker.record(False, 10.0), CircuitState.OPEN)
        self.assertEqual(breaker.state(15.0), CircuitState.OPEN)
        self.assertFalse(breaker.allow(15.0))
        self.assertEqual(breaker.state(20.0), CircuitState.HALF_OPEN)

    def test_half_open_success_closes(self):
        breaker = CircuitBreaker(threshold=2, cooldown=10.0)
        breaker.record(False, 0.0)
        breaker.record(False, 0.0)
        self.assertEqual(breaker.record(True, 10.0), CircuitState.CLOSED)
        self.assertEqual(breaker.consecutive_failures(), 0)
        self.assertTrue(breaker.allow(10.0))

    def test_open_failure_keeps_counter_and_cooldown(self):
        breaker = CircuitBreaker(threshold=2, cooldown=10.0)
        breaker.record(False, 0.0)
        breaker.record(False, 0.0)
        self.assertEqual(breaker.record(False, 5.0), CircuitState.OPEN)
        self.assertEqual(breaker.consecutive_failures(), 3)
        self.assertEqual(breaker.state(5.0), CircuitState.OPEN)
        self.assertEqual(breaker.state(10.0), CircuitState.HALF_OPEN)

    def test_reset_returns_to_closed(self):
        breaker = CircuitBreaker(threshold=2, cooldown=10.0)
        breaker.record(False, 0.0)
        breaker.record(False, 0.0)
        breaker.reset()
        self.assertEqual(breaker.consecutive_failures(), 0)
        self.assertEqual(breaker.state(0.0), CircuitState.CLOSED)
        self.assertTrue(breaker.allow(0.0))

    def test_default_threshold_matches_reference_invariant(self):
        self.assertEqual(MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES, 3)
        self.assertEqual(CircuitBreaker().threshold, 3)


class TestRecoveryLadder(unittest.TestCase):

    def test_ladder_order_cheapest_first(self):
        ladder = RecoveryLadder(["retry", "restart", "reclone"])
        self.assertIsNone(ladder.current())
        self.assertEqual(ladder.escalate(), "retry")
        self.assertEqual(ladder.current(), "retry")
        self.assertEqual(ladder.escalate(), "restart")
        self.assertEqual(ladder.escalate(), "reclone")
        self.assertEqual(ladder.attempts(), 3)

    def test_ladder_exhaustion_returns_none_and_does_not_wrap(self):
        ladder = RecoveryLadder(["retry", "restart"])
        self.assertEqual(ladder.escalate(), "retry")
        self.assertEqual(ladder.escalate(), "restart")
        self.assertTrue(ladder.exhausted())
        self.assertEqual(ladder.current(), "restart")
        self.assertIsNone(ladder.escalate())
        self.assertIsNone(ladder.escalate())
        self.assertEqual(ladder.attempts(), 2)
        self.assertTrue(ladder.exhausted())

    def test_escalate_until_predicate(self):
        ladder = RecoveryLadder(["retry", "restart", "reclone"])
        self.assertEqual(ladder.escalate_until(lambda s: s == "reclone"), "reclone")
        self.assertEqual(ladder.attempts(), 3)
        self.assertTrue(ladder.exhausted())

    def test_escalate_until_predicate_never_true(self):
        ladder = RecoveryLadder(["retry", "restart"])
        self.assertIsNone(ladder.escalate_until(lambda s: s == "missing"))
        self.assertTrue(ladder.exhausted())

    def test_escalate_until_continues_from_current_rung(self):
        ladder = RecoveryLadder(["retry", "restart", "reclone"])
        self.assertEqual(ladder.escalate(), "retry")
        self.assertEqual(ladder.escalate_until(lambda s: s == "reclone"), "reclone")
        self.assertEqual(ladder.attempts(), 3)

    def test_empty_ladder_raises(self):
        with self.assertRaises(ValueError):
            RecoveryLadder([])

    def test_duplicate_ladder_raises(self):
        with self.assertRaises(ValueError):
            RecoveryLadder(["retry", "retry"])

    def test_ladder_reset(self):
        ladder = RecoveryLadder(["retry", "restart"])
        ladder.escalate()
        ladder.escalate()
        ladder.reset()
        self.assertIsNone(ladder.current())
        self.assertEqual(ladder.attempts(), 0)
        self.assertFalse(ladder.exhausted())
        self.assertEqual(ladder.escalate(), "retry")


class TestGuardedRecovery(unittest.TestCase):

    def test_guarded_recovery_trips_without_escalating(self):
        ladder = RecoveryLadder(["retry", "restart", "reclone"])
        breaker = CircuitBreaker(threshold=2, cooldown=10.0)
        guarded = GuardedRecovery(ladder, breaker)

        first = guarded.step(False, 0.0)
        self.assertFalse(first["tripped"])
        self.assertEqual(first["step"], "retry")
        self.assertEqual(first["state"], CircuitState.CLOSED)

        second = guarded.step(False, 0.0)
        self.assertTrue(second["tripped"])
        self.assertIsNone(second["step"])
        self.assertEqual(second["state"], CircuitState.OPEN)
        self.assertEqual(ladder.current(), "retry")
        self.assertEqual(ladder.attempts(), 1)
        self.assertFalse(second["exhausted"])

    def test_guarded_recovery_escalates_when_healthy(self):
        ladder = RecoveryLadder(["retry", "restart"])
        breaker = CircuitBreaker(threshold=3, cooldown=10.0)
        guarded = GuardedRecovery(ladder, breaker)

        first = guarded.step(True, 0.0)
        self.assertEqual(first["step"], "retry")
        self.assertEqual(first["state"], CircuitState.CLOSED)
        self.assertFalse(first["tripped"])

        second = guarded.step(True, 0.0)
        self.assertEqual(second["step"], "restart")
        self.assertTrue(second["exhausted"])
        self.assertFalse(second["tripped"])

        third = guarded.step(True, 0.0)
        self.assertIsNone(third["step"])
        self.assertTrue(third["exhausted"])
        self.assertFalse(third["tripped"])

    def test_guarded_recovery_resumes_after_cooldown(self):
        ladder = RecoveryLadder(["retry", "restart"])
        breaker = CircuitBreaker(threshold=1, cooldown=10.0)
        guarded = GuardedRecovery(ladder, breaker)

        self.assertTrue(guarded.step(False, 0.0)["tripped"])
        self.assertEqual(ladder.attempts(), 0)
        resumed = guarded.step(True, 10.0)
        self.assertFalse(resumed["tripped"])
        self.assertEqual(resumed["step"], "retry")
        self.assertEqual(resumed["state"], CircuitState.CLOSED)


class TestDeterminism(unittest.TestCase):

    def test_deterministic_with_injected_now(self):
        sequence = [False, False, True, False, False, False]

        def run():
            breaker = CircuitBreaker(threshold=3, cooldown=5.0)
            observed = []
            now = 0.0
            for success in sequence:
                observed.append((breaker.record(success, now), breaker.state(now), breaker.allow(now)))
                now += 2.0
            return observed

        self.assertEqual(run(), run())

    def test_state_is_pure_for_same_now(self):
        breaker = CircuitBreaker(threshold=1, cooldown=5.0)
        breaker.record(False, 0.0)
        self.assertEqual(breaker.state(0.0), CircuitState.OPEN)
        self.assertEqual(breaker.state(0.0), CircuitState.OPEN)
        self.assertEqual(breaker.state(5.0), CircuitState.HALF_OPEN)
        self.assertEqual(breaker.state(5.0), CircuitState.HALF_OPEN)


if __name__ == "__main__":
    unittest.main()
