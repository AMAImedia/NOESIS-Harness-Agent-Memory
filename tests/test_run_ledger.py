"""Tests for the run-identity ledger in budget.py."""

import unittest

from noesis_harness.budget import (
    Budget,
    BudgetIdentityError,
    RunLedger,
    expected_rollouts,
    expected_sessions,
)


def _parallel(k):
    """A run that lands on the identity: k base + 2k candidates + k finals."""
    ledger = RunLedger(task_id="ledger-1", k=k, mode="agg")
    for i in range(1, k + 1):
        ledger.rollout("base%d" % i)
    for i in range(1, k + 1):
        ledger.session("inv%d" % i)
        ledger.session("dom%d" % i)
    for i in range(1, k + 1):
        ledger.rollout("inv%d" % i)
        ledger.rollout("dom%d" % i)
    for i in range(1, k + 1):
        ledger.session("agg%d" % i)
        ledger.rollout("agg%d" % i)
    return ledger


class ExpectedCountsTests(unittest.TestCase):
    def test_r_is_four_k_and_p_is_three_k(self):
        for k in (1, 2, 3, 7):
            with self.subTest(k=k):
                self.assertEqual(expected_rollouts(k), 4 * k)
                self.assertEqual(expected_sessions(k), 3 * k)

    def test_the_formula_is_closed_not_recorded(self):
        # Changing k changes what is expected; nothing can re-state it.
        self.assertNotEqual(expected_rollouts(1), expected_rollouts(2))


class RunLedgerTests(unittest.TestCase):
    def test_a_correct_run_passes_its_identity(self):
        for k in (1, 2, 3):
            with self.subTest(k=k):
                ledger = _parallel(k)
                self.assertEqual(ledger.R, 4 * k)
                self.assertEqual(ledger.P, 3 * k)
                self.assertEqual(ledger.assert_identity(), ledger)

    def test_a_short_run_fails(self):
        ledger = RunLedger(task_id="t", k=2, mode="agg")
        ledger.rollout("base1")
        with self.assertRaises(BudgetIdentityError) as caught:
            ledger.assert_identity()
        self.assertIn("R=1 (want 8)", str(caught.exception))

    def test_a_duplicate_label_is_caught_even_when_the_counts_line_up(self):
        ledger = _parallel(1)
        self.assertEqual((ledger.R, ledger.P), (4, 3))
        # A duplicate that happens to keep the counts is the dangerous case:
        # the run claims to have produced something it silently overwrote.
        ledger.entries.pop()
        ledger.rollout("inv1")
        self.assertEqual((ledger.R, ledger.P), (4, 3))
        with self.assertRaises(BudgetIdentityError) as caught:
            ledger.assert_identity()
        message = str(caught.exception)
        self.assertIn("DUPLICATE labels", message)
        self.assertIn("inv1", message)

    def test_duplicates_are_detected_before_the_counts(self):
        ledger = _parallel(2)
        ledger.rollout("base1")  # duplicate AND the count is now wrong
        self.assertEqual(ledger.duplicates(), {"rollout": ["base1"]})
        with self.assertRaises(BudgetIdentityError) as caught:
            ledger.assert_identity()
        self.assertIn("DUPLICATE labels", str(caught.exception))

    def test_duplicates_are_reported_per_kind(self):
        ledger = _parallel(1)
        ledger.session("inv1")
        self.assertEqual(ledger.duplicates(), {"session": ["inv1"]})

    def test_a_clean_run_reports_no_duplicates(self):
        self.assertEqual(_parallel(2).duplicates(), {})

    def test_retries_are_attempts_not_extra_units(self):
        ledger = _parallel(1)
        ledger.entries = [e for e in ledger.entries if not (e.kind == "session" and e.label == "inv1")]
        ledger.session("inv1", attempts=3)
        self.assertEqual(ledger.P, 3)
        self.assertEqual(ledger.to_dict()["session_attempts"], 5)
        ledger.assert_identity()

    def test_the_failure_names_the_labels_that_were_seen(self):
        ledger = RunLedger(task_id="t7", k=1, mode="seq")
        ledger.rollout("base1")
        with self.assertRaises(BudgetIdentityError) as caught:
            ledger.assert_identity()
        self.assertIn("seq-1 t7", str(caught.exception))
        self.assertIn("base1", str(caught.exception))

    def test_the_record_serialises_counts_expectations_and_duplicates(self):
        record = _parallel(1).to_dict()
        self.assertEqual(record["mode"], "agg")
        self.assertEqual(record["task_id"], "ledger-1")
        self.assertEqual(record["k"], 1)
        self.assertEqual(record["R"], record["expected_R"])
        self.assertEqual(record["P"], record["expected_P"])
        self.assertEqual(record["duplicates"], {})
        self.assertEqual(record["labels"]["rollout"], ["base1", "inv1", "dom1", "agg1"])


class BudgetTests(unittest.TestCase):
    """The existing spend cap is unchanged by the ledger addition."""

    def setUp(self):
        import tempfile
        from pathlib import Path

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self._path = str(Path(tmp.name) / "b.db")
        self.budget = Budget(self._path, daily_cap=3)

    def test_spend_needs_validation_first(self):
        self.assertEqual(self.budget.spend("a", validated=False)["reason"], "not_validated")
        self.assertEqual(self.budget.spend("a", validated=0)["reason"], "not_validated")

    def test_bad_units_are_refused(self):
        self.assertEqual(self.budget.spend("a", units=0, validated=True)["reason"], "bad_units")

    def test_the_daily_cap_is_enforced(self):
        budget = Budget(self._path, daily_cap=2)
        self.assertTrue(budget.spend("a", validated=True)["ok"])
        self.assertTrue(budget.spend("b", validated=True)["ok"])
        self.assertEqual(budget.spend("c", validated=True)["reason"], "exhausted")
        self.assertEqual(budget.remaining(), 0)

    def test_the_same_key_spends_once(self):
        self.assertTrue(self.budget.spend("a", validated=True)["ok"])
        self.assertTrue(self.budget.spend("a", validated=True).get("idempotent"))
        self.assertEqual(self.budget.remaining(), 2)

    def test_the_cap_is_checked_before_the_key_is_recognised(self):
        # Pre-existing behaviour, recorded so a future change to it is
        # deliberate: once the day is exhausted, even a key that was already
        # counted is refused rather than reported as a no-op.
        budget = Budget(self._path, daily_cap=3)
        budget.spend("a", validated=True)
        budget.spend("b", validated=True)
        budget.spend("c", validated=True)
        self.assertEqual(budget.spend("a", validated=True)["reason"], "exhausted")


__all__ = ["BudgetTests", "ExpectedCountsTests", "RunLedgerTests"]


if __name__ == "__main__":
    unittest.main()