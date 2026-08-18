import tempfile
import unittest
from pathlib import Path

from noesis_harness.multi_agent_benchmark import DurableWorkloadAggregator, MultiAgentBenchmarkError, MultiAgentWorkloadRunner, WorkloadCase


class MultiAgentBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.runner = MultiAgentWorkloadRunner(str(root / "workspaces"), str(root / "aggregate.db"), max_concurrency=3)
        self.cases = (
            WorkloadCase("case-a", "agent-a", "task-a", "alpha", reviewer_time_seconds=1.5),
            WorkloadCase("case-b", "agent-b", "task-b", "beta", fail_first=True, reviewer_time_seconds=2.5),
            WorkloadCase("case-c", "agent-c", "task-c", "gamma", reviewer_time_seconds=3.5),
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_parallel_workload_recovers_injected_crash_and_reports_metrics(self):
        run = self.runner.run(self.cases, run_id="run-1", retry_limit=1)
        self.assertEqual(len(run.results), 3)
        self.assertTrue(all(row["status"] == "passed" for row in run.results))
        recovered = next(row for row in run.results if row["task_id"] == "task-b")
        self.assertEqual(recovered["attempts"], 2)
        self.assertTrue(recovered["recovered"])
        self.assertEqual(run.metrics.cases, 3)
        self.assertEqual(run.metrics.correctness_rate, 1.0)
        self.assertEqual(run.metrics.recovery_rate, 1 / 3)
        self.assertAlmostEqual(run.metrics.mean_reviewer_time_seconds, 2.5)
        self.assertAlmostEqual(run.metrics.retry_rate, 1 / 3)

    def test_same_run_reopen_is_idempotent_and_conflict_is_denied(self):
        first = self.runner.run(self.cases, run_id="run-2", retry_limit=1)
        second = self.runner.run(self.cases, run_id="run-2", retry_limit=1)
        self.assertEqual(first.results, second.results)
        aggregator = DurableWorkloadAggregator(str(Path(self.tmp.name) / "aggregate.db"))
        with self.assertRaisesRegex(MultiAgentBenchmarkError, "workload_result_conflict"):
            aggregator.put("run-2", "task-a", {"status": "tampered"})

    def test_workload_identity_collisions_and_retry_bound_fail_closed(self):
        with self.assertRaisesRegex(MultiAgentBenchmarkError, "workload_identity_collision"):
            self.runner.run((WorkloadCase("a", "same", "task-1", "x"), WorkloadCase("b", "same", "task-2", "y")), run_id="bad")
        with self.assertRaisesRegex(Exception, "retry_limit_out_of_range"):
            self.runner.run(self.cases, run_id="bad-retry", retry_limit=4)


if __name__ == "__main__":
    unittest.main()
