"""Tests for the MA-07 deterministic workload runner."""
import tempfile
import unittest
from pathlib import Path

from noesis_harness.coordination import Actions
from noesis_harness.work_product_ma07 import (
    LaneSpec,
    WorkloadAggregateStore,
    WorkloadError,
    WorkProductWorkloadRunner,
)


class WorkloadAggregateStoreTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="noesis_ma07_store_")
        self.store = WorkloadAggregateStore(str(Path(self.root) / "agg.db"))

    def test_put_idempotent_and_conflict_rejected(self):
        self.store.put("run-1", "task-a", {"status": "completed", "attempts": 1})
        self.store.put("run-1", "task-a", {"status": "completed", "attempts": 1})
        with self.assertRaisesRegex(WorkloadError, "workload_aggregate_conflict"):
            self.store.put("run-1", "task-a", {"status": "failed", "attempts": 2})

    def test_projection_is_stable_and_ordered(self):
        self.store.put("run-1", "task-b", {"status": "completed"})
        self.store.put("run-1", "task-a", {"status": "completed"})
        first = self.store.project("run-1")
        second = self.store.project("run-1")
        self.assertEqual(first, second)
        self.assertEqual(list(first["tasks"]), ["task-a", "task-b"])
        self.assertTrue(first["aggregate_digest"].startswith("sha256:"))

    def test_empty_identity_fails_closed(self):
        with self.assertRaisesRegex(WorkloadError, "run_and_task_identity_required"):
            self.store.put("", "task-a", {})


class WorkProductWorkloadRunnerTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="noesis_ma07_runner_")

    @staticmethod
    def _specs():
        return (
            LaneSpec("agent-a", "task-a"),
            LaneSpec("agent-b", "task-b", crash_first_attempt=True),
            LaneSpec("agent-c", "task-c"),
        )

    def test_lane_count_bounds_fail_closed(self):
        runner = WorkProductWorkloadRunner(self.root)
        with self.assertRaisesRegex(WorkloadError, "lane_count_out_of_range"):
            runner.run("run-solo", (LaneSpec("a", "t"),))
        too_many = tuple(LaneSpec("agent-%d" % i, "task-%d" % i) for i in range(9))
        with self.assertRaisesRegex(WorkloadError, "lane_count_out_of_range"):
            runner.run("run-many", too_many)

    def test_multi_lane_run_recovers_injected_crash(self):
        runner = WorkProductWorkloadRunner(self.root)
        report = runner.run("run-crash", self._specs())
        self.assertEqual(report.statuses, ("passed", "passed", "passed"))
        self.assertIn("task-b", report.recovered_tasks)
        task_b_index = sorted(spec.task_id for spec in self._specs()).index("task-b")
        self.assertEqual(report.attempts[task_b_index], 2)
        actions = Actions(str(Path(self.root) / "workload-actions.db"))
        self.assertEqual(actions.counts().get("done"), 3)

    def test_completed_run_replay_is_identical(self):
        runner = WorkProductWorkloadRunner(self.root)
        first = runner.run("run-replay", self._specs())
        replay = runner.report("run-replay")
        self.assertEqual(first, replay)
        self.assertEqual(first.aggregate_digest, replay.aggregate_digest)

    def test_duplicate_run_aggregate_conflict_detected(self):
        runner_a = WorkProductWorkloadRunner(str(Path(self.root) / "a"))
        runner_b = WorkProductWorkloadRunner(str(Path(self.root) / "b"))
        first = runner_a.run("shared-run", self._specs())

        conflicting = (
            LaneSpec("agent-a", "task-a", crash_first_attempt=True),
            LaneSpec("agent-b", "task-b"),
            LaneSpec("agent-c", "task-c"),
        )
        runner_b.aggregate.forget("shared-run")
        runner_b.run("shared-run", conflicting)
        second = runner_b.report("shared-run")
        self.assertNotEqual(first.attempts, second.attempts)


if __name__ == "__main__":
    unittest.main()
