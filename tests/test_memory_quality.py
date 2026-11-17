import tempfile
import unittest
from pathlib import Path

from noesis_harness import Memory
from noesis_harness.isolation_holdouts import ActiveDelegationLeakageSuite
from noesis_harness.memory_quality import DurableMemoryQualityAdapter, DurableMemoryQualityTraceStore, MemoryQualityCase, MemoryQualityError, MemoryQualityEvaluator, MemoryTrajectoryStep, build_long_context_cases, compare_baseline_nextgen


class ActiveDelegationLeakageTests(unittest.TestCase):
    def test_concurrent_workspace_holdouts_all_pass(self):
        suite = ActiveDelegationLeakageSuite()
        results = suite.evaluate()
        self.assertEqual(tuple(result.case_id for result in results), suite.CASE_IDS)
        self.assertEqual(len(results), 6)
        self.assertTrue(all(result.passed for result in results), results)
        self.assertEqual(suite.pass_rate(), 1.0)


class MemoryQualityTests(unittest.TestCase):
    def test_quality_dimensions_are_separate_and_budget_is_hard(self):
        cases = (
            MemoryQualityCase("recall", ("s1", "s2"), ("s1",), ("s1",), True, True, ("s1",), ("s1", "s2"), 90, 100),
            MemoryQualityCase("conflict", ("s3",), ("s3", "noise"), ("noise",), False, True, ("s3",), ("s3",), 101, 100, leakage_free=False),
        )
        evaluator = MemoryQualityEvaluator()
        outcomes = evaluator.evaluate(cases)
        self.assertEqual(outcomes[0].recall, 0.5)
        self.assertEqual(outcomes[0].attribution_precision, 1.0)
        self.assertEqual(outcomes[0].compaction_retention, 0.5)
        self.assertTrue(outcomes[0].budget_respected)
        self.assertFalse(outcomes[1].budget_respected)
        metrics = evaluator.metrics(cases)
        self.assertEqual(metrics.cases, 2)
        self.assertEqual(metrics.budget_compliance_rate, 0.5)
        self.assertEqual(metrics.leakage_free_rate, 0.5)
        self.assertLess(metrics.quality_score, 1.0)

    def test_durable_trace_adapter_reopens_and_rejects_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory = Memory(str(Path(tmp) / "memory.db"))
            store = DurableMemoryQualityTraceStore(str(Path(tmp) / "quality.db"))
            adapter = DurableMemoryQualityAdapter(memory, store)
            case = MemoryQualityCase("durable", ("s1",), ("s1",), ("s1",), True, True, ("s1",), ("s1",), 8, 16)
            adapter.record("session-1", case)
            reopened = DurableMemoryQualityAdapter(Memory(str(Path(tmp) / "memory.db")), DurableMemoryQualityTraceStore(str(Path(tmp) / "quality.db")))
            self.assertEqual(reopened.evaluate_session("session-1").cases, 1)
            with self.assertRaisesRegex(MemoryQualityError, "trace_conflict"):
                reopened.record("session-1", MemoryQualityCase("durable", ("different",), ("s1",), ("s1",), True, True, ("s1",), ("s1",), 8, 16))

    def test_durable_context_reuse_trajectory_persists_and_measures_recall(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory = Memory(str(Path(tmp) / "memory.db"))
            store = DurableMemoryQualityTraceStore(str(Path(tmp) / "quality.db"))
            adapter = DurableMemoryQualityAdapter(memory, store)
            steps = (
                MemoryTrajectoryStep("step-1", "rollback", ("s1",), ("s1",), ("s1",), ("exp-1",), ("exp-1",), used_tokens=8, budget_tokens=16),
                MemoryTrajectoryStep("step-2", "conflict", ("s2",), ("s2", "noise"), ("s2",), ("exp-2",), ("exp-2", "exp-missing"), conflict_resolution_correct=True, used_tokens=15, budget_tokens=16),
            )
            metrics = adapter.record_trajectory("trajectory-1", steps)
            self.assertEqual(metrics.cases, 2)
            self.assertEqual(metrics.experience_reuse_recall_mean, 0.75)
            reopened = DurableMemoryQualityAdapter(Memory(str(Path(tmp) / "memory.db")), DurableMemoryQualityTraceStore(str(Path(tmp) / "quality.db")))
            self.assertEqual(reopened.evaluate_session("trajectory-1").experience_reuse_recall_mean, 0.75)
            records = reopened.trace_store.list_session("trajectory-1")
            self.assertEqual(records[0]["query"], "rollback")
            self.assertEqual(records[0]["reused_experience_ids"], ["exp-1"])

    def test_multi_session_quality_aggregation_is_durable_and_session_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory_path = str(Path(tmp) / "memory.db")
            quality_path = str(Path(tmp) / "quality.db")
            adapter = DurableMemoryQualityAdapter(Memory(memory_path), DurableMemoryQualityTraceStore(quality_path))
            adapter.record_trajectory("session-a", (MemoryTrajectoryStep("step", "rollback", ("source-a",), ("source-a",), ("source-a",), used_tokens=8, budget_tokens=16),))
            adapter.record_trajectory("session-b", (MemoryTrajectoryStep("step", "resume", ("source-b",), ("source-b",), ("source-b",), used_tokens=12, budget_tokens=16),))
            report = adapter.evaluate_sessions(("session-a", "session-b"))
            self.assertEqual(report.session_count, 2)
            self.assertEqual(report.total_cases, 2)
            self.assertEqual(report.aggregate_metrics.cases, 2)
            self.assertEqual(report.session_metrics["session-a"].cases, 1)
            reopened = DurableMemoryQualityAdapter(Memory(memory_path), DurableMemoryQualityTraceStore(quality_path))
            reopened_report = reopened.evaluate_sessions(("session-a", "session-b"))
            self.assertEqual(reopened_report.aggregate_metrics.quality_score, report.aggregate_metrics.quality_score)
            self.assertEqual(reopened_report.aggregate_metrics.experience_reuse_recall_mean, 1.0)

    def test_multi_session_missing_trace_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = DurableMemoryQualityAdapter(Memory(str(Path(tmp) / "memory.db")), DurableMemoryQualityTraceStore(str(Path(tmp) / "quality.db")))
            with self.assertRaisesRegex(MemoryQualityError, "session_traces_required"):
                adapter.evaluate_sessions(("missing-session",))
            with self.assertRaisesRegex(MemoryQualityError, "session_ids_required"):
                adapter.evaluate_sessions(())

    def test_trajectory_conflict_and_budget_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory = Memory(str(Path(tmp) / "memory.db"))
            store = DurableMemoryQualityTraceStore(str(Path(tmp) / "quality.db"))
            adapter = DurableMemoryQualityAdapter(memory, store)
            step = MemoryTrajectoryStep("step", "rollback", ("s1",), ("s1", "leak"), ("s1", "leak"), used_tokens=17, budget_tokens=16, leakage_free=False)
            metrics = adapter.record_trajectory("adversarial", (step,))
            self.assertEqual(metrics.budget_compliance_rate, 0.0)
            self.assertEqual(metrics.attribution_precision_mean, 0.5)
            self.assertEqual(metrics.leakage_free_rate, 0.0)
            with self.assertRaisesRegex(MemoryQualityError, "trace_conflict"):
                adapter.record("adversarial", MemoryQualityCase("step", ("s1",), ("s1",), ("s1",), True, True, (), (), 1, 16), query="different-query")

    def test_real_memory_decay_is_bounded_and_persistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "memory.db")
            memory = Memory(path)
            memory_id = memory.save("durable rollback fact", confidence=0.9)
            before = memory.profile()[0]["strength"]
            memory.decay(periods=100)
            after = memory.profile()[0]["strength"]
            self.assertGreaterEqual(after, Memory.DECAY_FLOOR)
            self.assertLess(after, before)
            reopened = Memory(path)
            self.assertEqual(reopened.profile()[0]["id"], memory_id)
            self.assertGreaterEqual(reopened.profile()[0]["strength"], Memory.DECAY_FLOOR)

    def test_long_context_budget_and_baseline_nextgen_distribution(self):
        cases = build_long_context_cases((32, 128, 512), budget_tokens=64)
        report = compare_baseline_nextgen(cases, repetitions=3)
        self.assertEqual(report.repetitions, 3)
        self.assertEqual(report.cases, 3)
        self.assertEqual(report.nextgen_budget_compliance, 1.0)
        self.assertEqual(report.baseline_budget_compliance, 1.0)
        self.assertGreater(report.nextgen_recall_mean, report.baseline_recall_mean)
        self.assertGreater(report.recall_gain_mean, 0.0)

    def test_real_memory_reuse_stress_reopens_and_is_deterministic(self):
        from noesis_harness.memory_quality import run_real_memory_reuse_stress
        with tempfile.TemporaryDirectory() as tmp:
            report = run_real_memory_reuse_stress(str(Path(tmp) / "memory.db"), str(Path(tmp) / "quality.db"), repetitions=4, scale=24)
            self.assertEqual(report.repetitions, 4)
            self.assertEqual(report.session_count, 4)
            self.assertEqual(report.total_cases, 8)
            self.assertEqual(report.recall_mean, 1.0)
            self.assertEqual(report.recall_distribution, (1.0, 1.0, 1.0, 1.0))
            self.assertTrue(report.persistence_verified)
            reopened = run_real_memory_reuse_stress(str(Path(tmp) / "memory.db"), str(Path(tmp) / "quality-2.db"), repetitions=4, scale=24)
            self.assertEqual(reopened.distribution_digest, report.distribution_digest)
            different_shape = run_real_memory_reuse_stress(str(Path(tmp) / "memory.db"), str(Path(tmp) / "quality-3.db"), repetitions=4, scale=24, trajectory_width=1)
            self.assertNotEqual(different_shape.distribution_digest, report.distribution_digest)

    def test_durable_long_context_stress_persists_repeated_distribution(self):
        from noesis_harness.memory_quality import run_durable_long_context_stress
        with tempfile.TemporaryDirectory() as tmp:
            report = run_durable_long_context_stress(str(Path(tmp) / "long-context.db"), scales=(8, 16), repetitions=3)
            self.assertEqual(report.cases, 2)
            self.assertEqual(report.trace_sessions, 3)
            self.assertEqual(report.baseline_recall_distribution, (0.0, 0.0, 0.0))
            self.assertEqual(report.nextgen_recall_distribution, (1.0, 1.0, 1.0))
            self.assertTrue(report.persistence_verified)
            reopened = run_durable_long_context_stress(str(Path(tmp) / "long-context.db"), scales=(8, 16), repetitions=3)
            self.assertEqual(reopened.distribution_digest, report.distribution_digest)

    def test_real_memory_reuse_stress_rejects_unbounded_parameters(self):
        from noesis_harness.memory_quality import run_real_memory_reuse_stress
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(MemoryQualityError, "real_stress_parameters_invalid"):
                run_real_memory_reuse_stress(str(Path(tmp) / "memory.db"), str(Path(tmp) / "quality.db"), repetitions=0)
            with self.assertRaisesRegex(MemoryQualityError, "real_stress_parameters_invalid"):
                run_real_memory_reuse_stress(str(Path(tmp) / "memory.db"), str(Path(tmp) / "quality.db"), scale=0)
            with self.assertRaisesRegex(MemoryQualityError, "real_stress_parameters_invalid"):
                run_real_memory_reuse_stress(str(Path(tmp) / "memory.db"), str(Path(tmp) / "quality.db"), trajectory_width=9)

    def test_duplicate_and_empty_memory_cases_fail_closed(self):
        evaluator = MemoryQualityEvaluator()
        case = MemoryQualityCase("same", (), (), (), True, True, (), (), 0, 10)
        with self.assertRaisesRegex(MemoryQualityError, "duplicate_case_id"):
            evaluator.evaluate((case, case))
        with self.assertRaisesRegex(MemoryQualityError, "cases_required"):
            evaluator.metrics(())
        with self.assertRaisesRegex(MemoryQualityError, "case_and_budget_required"):
            MemoryQualityCase("", (), (), (), True, True, (), (), 0, 10)


if __name__ == "__main__":
    unittest.main()
