import os
import tempfile
import unittest
from pathlib import Path

from noesis_harness.best_state import (
    BestStateStore,
    DecisionStatus,
    RecoveryStatus,
)


class BestStateTests(unittest.TestCase):
    def test_best_state_is_monotonic_and_late_regression_is_not_best(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "best.db"
            store = BestStateStore(str(db))
            first = store.record_candidate("run-1", 0.40, {"step": 1})
            best = store.record_candidate("run-1", 0.80, {"step": 2})
            regression = store.record_candidate("run-1", 0.30, {"step": 3})
            self.assertEqual(first.status, DecisionStatus.BEST_ACCEPTED)
            self.assertEqual(best.status, DecisionStatus.BEST_ACCEPTED)
            self.assertEqual(regression.status, DecisionStatus.ACCEPTED_NOT_BEST)
            self.assertEqual(store.best("run-1").score, 0.80)
            self.assertEqual(store.current("run-1").score, 0.30)
            self.assertEqual(len(store.history("run-1")), 3)

    def test_failed_verification_never_becomes_current_or_best(self):
        with tempfile.TemporaryDirectory() as d:
            store = BestStateStore(str(Path(d) / "best.db"))
            accepted = store.record_candidate("run-2", 0.50, {"ok": True})
            rejected = store.record_candidate("run-2", 0.99, {"bad": True}, verifier_status="failed")
            self.assertEqual(accepted.status, DecisionStatus.BEST_ACCEPTED)
            self.assertEqual(rejected.status, DecisionStatus.REJECTED_VERIFICATION)
            self.assertEqual(store.best("run-2").score, 0.50)
            self.assertEqual(store.current("run-2").score, 0.50)

    def test_automatic_recovery_restores_best_and_records_event(self):
        with tempfile.TemporaryDirectory() as d:
            store = BestStateStore(str(Path(d) / "best.db"))
            best = store.record_candidate("run-3", 0.90, {"version": "best"})
            regression = store.record_candidate("run-3", 0.20, {"version": "regression"})
            recovered = store.recover("run-3", "late-regression")
            self.assertEqual(recovered.status, RecoveryStatus.RECOVERED)
            self.assertEqual(recovered.from_state_id, regression.state.state_id)
            self.assertEqual(recovered.to_state_id, best.state.state_id)
            self.assertEqual(store.current("run-3").state_id, best.state.state_id)
            self.assertEqual(store.best("run-3").state_id, best.state.state_id)
            self.assertEqual(store.rollback_count("run-3"), 1)
            again = store.recover("run-3", "idempotent-recovery")
            self.assertEqual(again.status, RecoveryStatus.NOOP)
            self.assertEqual(store.rollback_count("run-3"), 1)

    def test_manual_rollback_to_verified_older_state(self):
        with tempfile.TemporaryDirectory() as d:
            store = BestStateStore(str(Path(d) / "best.db"))
            first = store.record_candidate("run-4", 0.30, {"version": 1})
            second = store.record_candidate("run-4", 0.60, {"version": 2})
            third = store.record_candidate("run-4", 0.75, {"version": 3})
            result = store.rollback("run-4", first.state.state_id, "operator-review")
            self.assertEqual(result.status, RecoveryStatus.RECOVERED)
            self.assertEqual(store.current("run-4").state_id, first.state.state_id)
            self.assertEqual(store.best("run-4").state_id, third.state.state_id)
            self.assertEqual(store.rollback_count("run-4"), 1)

    def test_missing_run_recovers_fail_soft(self):
        with tempfile.TemporaryDirectory() as d:
            store = BestStateStore(str(Path(d) / "best.db"))
            result = store.recover("missing")
            self.assertEqual(result.status, RecoveryStatus.UNAVAILABLE)
            self.assertEqual(result.run_id, "missing")

    def test_sqlite_handles_windows_style_cleanup(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "best.db"
            store = BestStateStore(str(db))
            store.record_candidate("run-5", 1.0, {"done": True})
            for suffix in ("", "-wal", "-shm"):
                path = Path(str(db) + suffix)
                if path.exists():
                    path.unlink()
            self.assertFalse(db.exists())


if __name__ == "__main__":
    unittest.main()
