import tempfile
import unittest
from pathlib import Path

from noesis_harness.best_state import BestStateStore
from noesis_harness.fibers import FiberStore
from noesis_harness.orchestration import WorkCoordinator
from noesis_harness.recovery import RecoveryCoordinator


class RecoveryIntegrationTests(unittest.TestCase):
    def test_crash_recovery_restores_best_fiber_and_reclaims_expired_lease(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            best = BestStateStore(str(root / "state.db"))
            fibers = FiberStore(str(root / "state.db"))
            work = WorkCoordinator(str(root / "state.db"))
            fiber_id = fibers.register("research", {"topic": "rollback"})
            work.add("task-1")
            claim = work.claim("agent-a", ttl=10.0, now=100.0)
            self.assertIsNotNone(claim)
            first = best.record_candidate("run-1", 0.9, {"answer": "verified"}, metadata={"fiber_step": 4})
            fibers.checkpoint(fiber_id, 4, {"answer": "verified"})
            regression = best.record_candidate("run-1", 0.1, {"answer": "bad"}, metadata={"fiber_step": 5})
            fibers.checkpoint(fiber_id, 5, {"answer": "bad"})
            report = RecoveryCoordinator(best, fibers, work).recover_after_crash("run-1", fiber_id, "task-1", now=111.0)
            self.assertEqual(report.recovery_status, "recovered")
            self.assertEqual(report.best_state_id, first.state.state_id)
            self.assertEqual(report.fiber_step, 4)
            self.assertEqual(report.fiber_status, "restored")
            self.assertEqual(report.reclaimed_leases, 1)
            self.assertEqual(work.status("task-1")["status"], "pending")
            self.assertEqual(best.current("run-1").state_id, first.state.state_id)
            self.assertNotEqual(regression.state.state_id, best.current("run-1").state_id)

    def test_live_lease_is_not_reclaimed_and_missing_best_is_fail_soft(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            best = BestStateStore(str(root / "state.db"))
            fibers = FiberStore(str(root / "state.db"))
            work = WorkCoordinator(str(root / "state.db"))
            fiber_id = fibers.register("research")
            work.add("task-live")
            work.claim("agent-live", ttl=100.0, now=100.0)
            report = RecoveryCoordinator(best, fibers, work).recover_after_crash("missing", fiber_id, "task-live", now=101.0)
            self.assertEqual(report.recovery_status, "unavailable")
            self.assertEqual(report.reclaimed_leases, 0)
            self.assertEqual(work.status("task-live")["status"], "leased")
            self.assertEqual(report.fiber_status, "checkpointed")


if __name__ == "__main__":
    unittest.main()
