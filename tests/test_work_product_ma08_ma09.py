"""Tests for MA-08 and MA-09 workload probes."""
import unittest
import statistics

from noesis_harness.work_product_ma08_ma09 import (
    CrashInjectionProber,
    ActiveDelegationProber,
    CrashInjectionSummary,
    ActiveDelegationSummary,
)


class CrashInjectionProberTests(unittest.TestCase):
    """Tests for MA-08 crash injection prober."""

    def test_default_repetitions_bounded(self):
        prober = CrashInjectionProber()
        self.assertEqual(prober.repetitions, 10)

    def test_custom_repetitions_clamped(self):
        prober = CrashInjectionProber(repetitions=100)
        self.assertEqual(prober.repetitions, 50)  # MAX_REPETITIONS

        prober = CrashInjectionProber(repetitions=0)
        self.assertEqual(prober.repetitions, 1)

    def test_phases_defined(self):
        prober = CrashInjectionProber()
        self.assertEqual(prober.PHASES, ("pre_write", "post_write", "pre_read", "post_read", "workspace_escape"))

    def test_single_pass_returns_all_phases(self):
        prober = CrashInjectionProber(repetitions=1, seed=42)
        results = prober.run_single_pass()
        self.assertEqual(len(results), 5)
        phases = {r.phase for r in results}
        self.assertEqual(phases, set(prober.PHASES))

    def test_repeated_runs_collects_results(self):
        prober = CrashInjectionProber(repetitions=5, seed=123)
        all_results = prober.run_repeated()
        for phase in prober.PHASES:
            self.assertEqual(len(all_results[phase]), 5)

    def test_summarize_computes_statistics(self):
        prober = CrashInjectionProber(repetitions=10, seed=456)
        all_results = prober.run_repeated()
        summaries = prober.summarize(all_results)

        self.assertEqual(len(summaries), 5)
        for summary in summaries:
            self.assertIsInstance(summary, CrashInjectionSummary)
            self.assertEqual(summary.runs, 10)
            self.assertGreaterEqual(summary.mean_ms, 0)
            self.assertGreaterEqual(summary.p50_ms, 0)
            self.assertGreaterEqual(summary.p95_ms, 0)
            self.assertGreaterEqual(summary.survival_rate, 0)
            self.assertLessEqual(summary.survival_rate, 1)
            self.assertLessEqual(summary.min_ms, summary.max_ms)

    def test_summarize_p50_p95_ordering(self):
        """Verify p50 <= p95 for all phases."""
        prober = CrashInjectionProber(repetitions=20, seed=789)
        all_results = prober.run_repeated()
        summaries = prober.summarize(all_results)
        for summary in summaries:
            self.assertLessEqual(summary.p50_ms, summary.p95_ms + 1e-9)

    def test_full_run_returns_summaries(self):
        prober = CrashInjectionProber(repetitions=8, seed=999)
        summaries = prober.run_full()
        self.assertEqual(len(summaries), 5)
        for s in summaries:
            self.assertEqual(s.runs, 8)

    def test_deterministic_with_same_seed(self):
        """Same seed should produce identical results."""
        prober1 = CrashInjectionProber(repetitions=10, seed=42)
        prober2 = CrashInjectionProber(repetitions=10, seed=42)
        summaries1 = prober1.run_full()
        summaries2 = prober2.run_full()
        for s1, s2 in zip(summaries1, summaries2):
            self.assertEqual(s1.mean_ms, s2.mean_ms)
            self.assertEqual(s1.p50_ms, s2.p50_ms)
            self.assertEqual(s1.p95_ms, s2.p95_ms)
            self.assertEqual(s1.survival_rate, s2.survival_rate)

    def test_different_seeds_produce_different_results(self):
        """Different seeds change the deterministic injection distribution."""
        prober1 = CrashInjectionProber(repetitions=20, seed=1)
        prober2 = CrashInjectionProber(repetitions=20, seed=2)
        runs1 = prober1.run_repeated()
        runs2 = prober2.run_repeated()
        patterns1 = {phase: tuple(r.injected for r in runs1[phase]) for phase in prober1.PHASES}
        patterns2 = {phase: tuple(r.injected for r in runs2[phase]) for phase in prober2.PHASES}
        self.assertNotEqual(patterns1, patterns2)


class ActiveDelegationProberTests(unittest.TestCase):
    """Tests for MA-09 active delegation prober."""

    def test_case_ids_defined(self):
        prober = ActiveDelegationProber()
        self.assertEqual(prober.CASE_IDS, ("sibling_read_denied", "sibling_write_denied", "absolute_path_denied", "traversal_denied"))

    def test_simultaneous_run_returns_all_cases(self):
        prober = ActiveDelegationProber()
        summary = prober.run_simultaneous()
        self.assertIsInstance(summary, ActiveDelegationSummary)
        self.assertEqual(len(summary.results), 4)
        self.assertEqual(summary.case_ids, prober.CASE_IDS)

    def test_all_probes_pass_boundary_enforcement(self):
        """All four probes should be denied (pass = boundary enforced)."""
        prober = ActiveDelegationProber()
        summary = prober.run_simultaneous()
        self.assertTrue(summary.all_passed, f"Some probes failed: {[(r.case_id, r.observed, r.passed) for r in summary.results]}")
        for result in summary.results:
            self.assertTrue(result.passed, f"{result.case_id} was allowed: {result.observed}")
            self.assertIn("denied", result.observed.lower())

    def test_durations_reported(self):
        prober = ActiveDelegationProber()
        summary = prober.run_simultaneous()
        self.assertGreater(summary.mean_duration_ms, 0)
        self.assertGreaterEqual(summary.max_duration_ms, summary.mean_duration_ms)
        for result in summary.results:
            self.assertGreaterEqual(result.duration_ms, 0)

    def test_repeated_runs_stable(self):
        """Repeated runs should consistently pass."""
        prober = ActiveDelegationProber()
        summaries = prober.run_repeated(repetitions=5)
        self.assertEqual(len(summaries), 5)
        for summary in summaries:
            self.assertTrue(summary.all_passed, "Repeated run failed")

    def test_sibling_read_denied(self):
        prober = ActiveDelegationProber()
        summary = prober.run_simultaneous()
        sibling_read = next(r for r in summary.results if r.case_id == "sibling_read_denied")
        self.assertTrue(sibling_read.passed)
        self.assertIn("denied", sibling_read.observed.lower())

    def test_sibling_write_denied(self):
        prober = ActiveDelegationProber()
        summary = prober.run_simultaneous()
        sibling_write = next(r for r in summary.results if r.case_id == "sibling_write_denied")
        self.assertTrue(sibling_write.passed)
        self.assertIn("denied", sibling_write.observed.lower())

    def test_absolute_path_denied(self):
        prober = ActiveDelegationProber()
        summary = prober.run_simultaneous()
        abs_path = next(r for r in summary.results if r.case_id == "absolute_path_denied")
        self.assertTrue(abs_path.passed)
        self.assertIn("denied", abs_path.observed.lower())

    def test_traversal_denied(self):
        prober = ActiveDelegationProber()
        summary = prober.run_simultaneous()
        traversal = next(r for r in summary.results if r.case_id == "traversal_denied")
        self.assertTrue(traversal.passed)
        self.assertIn("denied", traversal.observed.lower())


class IntegrationTests(unittest.TestCase):
    """Integration tests combining MA-08 and MA-09."""

    def test_both_probers_execute_without_error(self):
        """Both prober classes should execute without raising exceptions."""
        crash_prober = CrashInjectionProber(repetitions=3, seed=42)
        crash_summaries = crash_prober.run_full()
        self.assertEqual(len(crash_summaries), 5)

        delegation_prober = ActiveDelegationProber()
        delegation_summary = delegation_prober.run_simultaneous()
        self.assertTrue(delegation_summary.all_passed)

    def test_crash_prober_workspace_escape_included(self):
        """Workspace escape probe should be part of crash injection suite."""
        prober = CrashInjectionProber(repetitions=1, seed=1)
        summaries = prober.run_full()
        escape_summary = next(s for s in summaries if s.phase == "workspace_escape")
        self.assertEqual(escape_summary.runs, 1)
        self.assertEqual(escape_summary.survival_rate, 1.0)  # Should always survive (be contained)

    def test_statistical_reporting_deterministic(self):
        """Mean/p50/p95 should be deterministic for same seed."""
        prober1 = CrashInjectionProber(repetitions=15, seed=12345)
        prober2 = CrashInjectionProber(repetitions=15, seed=12345)
        s1 = prober1.run_full()
        s2 = prober2.run_full()
        for sum1, sum2 in zip(s1, s2):
            self.assertEqual(sum1.mean_ms, sum2.mean_ms)
            self.assertEqual(sum1.p50_ms, sum2.p50_ms)
            self.assertEqual(sum1.p95_ms, sum2.p95_ms)


if __name__ == "__main__":
    unittest.main()