"""tests/test_verification_ledger.py

Unit tests for noesis_harness.verification_ledger.

Covers the verification ledger, the capped fix loop, and the pre-run marker
guard ported from the AI-Builder-Club/skills templates.

Stdlib only. Run: python -m unittest tests.test_verification_ledger -q
"""

import unittest

from noesis_harness.verification_ledger import (
    AppliedChange,
    FixLoop,
    LedgerError,
    MarkerGuard,
    VerificationLedger,
)


class TestVerificationLedgerRecordAndDue(unittest.TestCase):
    def test_record_sets_verify_after(self):
        ledger = VerificationLedger()
        change = ledger.record("c1", "tune title", now=1000.0, verify_after_days=2)
        self.assertIsInstance(change, AppliedChange)
        self.assertEqual(change.applied_at, 1000.0)
        self.assertEqual(change.verify_after, 1000.0 + 2 * 86400.0)
        self.assertFalse(change.verified)

    def test_due_before_verify_after_is_empty(self):
        ledger = VerificationLedger()
        ledger.record("c1", "a", now=0.0, verify_after_days=1)
        self.assertEqual(ledger.due(80000.0), [])

    def test_due_at_or_after_verify_after_includes_change(self):
        ledger = VerificationLedger()
        ledger.record("c1", "a", now=0.0, verify_after_days=1)
        exact = ledger.due(86400.0)
        self.assertEqual([change.change_id for change in exact], ["c1"])
        later = ledger.due(200000.0)
        self.assertEqual([change.change_id for change in later], ["c1"])

    def test_due_sorted_by_verify_after_then_id(self):
        ledger = VerificationLedger()
        ledger.record("b", "later", now=0.0, verify_after_days=2)
        ledger.record("a", "sooner", now=0.0, verify_after_days=1)
        ledger.record("c", "same-as-a", now=0.0, verify_after_days=1)
        ids = [change.change_id for change in ledger.due(3 * 86400.0)]
        self.assertEqual(ids, ["a", "c", "b"])

    def test_duplicate_change_id_raises(self):
        ledger = VerificationLedger()
        ledger.record("c1", "a", now=0.0, verify_after_days=1)
        with self.assertRaises(LedgerError):
            ledger.record("c1", "again", now=5.0, verify_after_days=1)


class TestVerificationLedgerVerify(unittest.TestCase):
    def test_verify_marks_observed_and_verified(self):
        ledger = VerificationLedger()
        ledger.record("c1", "a", now=0.0, verify_after_days=1, baseline=10.0)
        result = ledger.verify("c1", observed=12.5, now=86400.0)
        self.assertTrue(result.verified)
        self.assertEqual(result.observed, 12.5)
        self.assertEqual(ledger.due(10 * 86400.0), [])

    def test_verify_unknown_raises(self):
        ledger = VerificationLedger()
        with self.assertRaises(LedgerError):
            ledger.verify("missing", observed=1.0, now=0.0)

    def test_verify_twice_raises(self):
        ledger = VerificationLedger()
        ledger.record("c1", "a", now=0.0, verify_after_days=1)
        ledger.verify("c1", observed=1.0, now=1.0)
        with self.assertRaises(LedgerError):
            ledger.verify("c1", observed=2.0, now=2.0)


class TestVerificationLedgerAdvice(unittest.TestCase):
    def test_recommendations_only_for_verified_regressions(self):
        ledger = VerificationLedger()
        ledger.record("reg", "regression", now=0.0, verify_after_days=0, baseline=10.0)
        ledger.record("ok", "improved", now=0.0, verify_after_days=0, baseline=10.0)
        ledger.record("open", "unverified", now=0.0, verify_after_days=0, baseline=10.0)
        ledger.verify("reg", observed=7.0, now=1.0)
        ledger.verify("ok", observed=13.0, now=1.0)
        advice = ledger.recommendations()
        self.assertEqual(len(advice), 1)
        self.assertEqual(advice[0]["change_id"], "reg")
        self.assertEqual(advice[0]["kind"], "revert_recommended")
        self.assertAlmostEqual(advice[0]["delta"], -3.0)

    def test_no_recommendation_when_improved(self):
        ledger = VerificationLedger()
        ledger.record("ok", "improved", now=0.0, verify_after_days=0, baseline=5.0)
        ledger.verify("ok", observed=5.0, now=1.0)
        self.assertEqual(ledger.recommendations(), [])

    def test_recommendations_sorted_by_change_id(self):
        ledger = VerificationLedger()
        ledger.record("z", "z", now=0.0, verify_after_days=0, baseline=1.0)
        ledger.record("a", "a", now=0.0, verify_after_days=0, baseline=1.0)
        ledger.verify("z", observed=0.0, now=1.0)
        ledger.verify("a", observed=0.0, now=1.0)
        ids = [entry["change_id"] for entry in ledger.recommendations()]
        self.assertEqual(ids, ["a", "z"])

    def test_open_changes_sorted(self):
        ledger = VerificationLedger()
        ledger.record("b", "b", now=0.0, verify_after_days=1)
        ledger.record("a", "a", now=0.0, verify_after_days=1)
        self.assertEqual(ledger.open_changes(), ["a", "b"])
        ledger.verify("a", observed=1.0, now=1.0)
        self.assertEqual(ledger.open_changes(), ["b"])

    def test_findings_counts(self):
        ledger = VerificationLedger()
        ledger.record("reg", "reg", now=0.0, verify_after_days=1, baseline=10.0)
        ledger.record("good", "good", now=0.0, verify_after_days=1, baseline=10.0)
        ledger.record("open", "open", now=0.0, verify_after_days=1)
        ledger.verify("reg", observed=4.0, now=1.0)
        ledger.verify("good", observed=11.0, now=1.0)
        report = ledger.findings()
        self.assertEqual(report["total"], 3)
        self.assertEqual(report["verified"], 2)
        self.assertEqual(report["unverified"], 1)
        self.assertEqual(report["regressions"], 1)
        self.assertEqual(report["due_pending"], 0)

    def test_findings_due_pending_uses_latest_now(self):
        ledger = VerificationLedger()
        ledger.record("c1", "c1", now=0.0, verify_after_days=1)
        self.assertEqual(ledger.findings()["due_pending"], 0)
        ledger.due(86400.0)
        self.assertEqual(ledger.findings()["due_pending"], 1)

    def test_determinism_same_history_same_report(self):
        def build():
            ledger = VerificationLedger()
            ledger.record("c1", "a", now=100.0, verify_after_days=3, baseline=9.0)
            ledger.record("c2", "b", now=100.0, verify_after_days=1, baseline=2.0)
            ledger.verify("c2", observed=1.0, now=200.0)
            return ledger

        first = build()
        second = build()
        self.assertEqual(first.findings(), second.findings())
        self.assertEqual(first.recommendations(), second.recommendations())
        self.assertEqual(first.open_changes(), second.open_changes())
        self.assertEqual(first.due(300000.0), second.due(300000.0))


class TestFixLoop(unittest.TestCase):
    def test_rejects_non_positive_max_rounds(self):
        with self.assertRaises(ValueError):
            FixLoop(max_rounds=0)
        with self.assertRaises(ValueError):
            FixLoop(max_rounds=True)

    def test_success_first_round(self):
        loop = FixLoop(max_rounds=3)
        calls = []
        result = loop.run(lambda index: calls.append(index) or True)
        self.assertEqual(result, {"ok": True, "rounds": 1, "escalated": False})
        self.assertEqual(calls, [0])

    def test_success_later_round(self):
        loop = FixLoop(max_rounds=4)
        result = loop.run(lambda index: index == 2)
        self.assertEqual(result, {"ok": True, "rounds": 3, "escalated": False})

    def test_exhaustion_escalates(self):
        loop = FixLoop(max_rounds=3)
        result = loop.run(lambda index: False)
        self.assertEqual(result, {"ok": False, "rounds": 3, "escalated": True})

    def test_attempt_receives_each_round_index(self):
        loop = FixLoop(max_rounds=3)
        seen = []
        loop.run(lambda index: seen.append(index) and False)
        self.assertEqual(seen, [0, 1, 2])

    def test_each_round_is_a_fresh_call(self):
        loop = FixLoop(max_rounds=3)
        calls = []

        def attempt(index):
            calls.append(index)
            return len(calls) == 2

        result = loop.run(attempt)
        self.assertEqual(calls, [0, 1])
        self.assertEqual(result["rounds"], 2)


class TestMarkerGuard(unittest.TestCase):
    def test_count_occurrences(self):
        guard = MarkerGuard()
        self.assertEqual(guard.count("clean text"), 0)
        self.assertEqual(guard.count("<FILL: a and <FILL: b"), 2)

    def test_check_clean_and_dirty(self):
        guard = MarkerGuard()
        self.assertEqual(guard.check("all set"), (True, 0))
        self.assertEqual(guard.check("<FILL: gap"), (False, 1))

    def test_require_clean_passes_when_clean(self):
        guard = MarkerGuard()
        self.assertIsNone(guard.require_clean("ready"))

    def test_require_clean_raises_with_count(self):
        guard = MarkerGuard()
        with self.assertRaises(LedgerError) as ctx:
            guard.require_clean("<FILL: a\n<FILL: b")
        self.assertEqual(str(ctx.exception), "2 template markers remain")

    def test_custom_marker(self):
        guard = MarkerGuard(marker="TODO:")
        self.assertEqual(guard.count("TODO: x TODO: y"), 2)
        self.assertEqual(guard.check("no markers"), (True, 0))

    def test_empty_marker_rejected(self):
        with self.assertRaises(ValueError):
            MarkerGuard(marker="")


if __name__ == "__main__":
    unittest.main()
