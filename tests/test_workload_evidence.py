"""Tests for the deterministic Gate 4 workload-evidence generator.

The builder is invoked directly (no subprocess) following the sibling
evidence-script test conventions; assertions cover schema shape, the MA-07
injected-crash recovery contract, byte stability across builds, digest
integrity, and the absence of any timestamp-like key or value.
"""
from __future__ import annotations

import json
import re
import unittest

from scripts.run_workload_evidence import (
    CLAIM_BOUNDARY,
    EVALUATOR_OUTCOMES,
    SCHEMA_VERSION,
    build_evidence,
    canonical_digest,
)

TIMESTAMP_PATTERN = re.compile(r"20[0-9]{2}-|_at\b")

TOP_LEVEL_KEYS = (
    "schema_version",
    "claim_boundary",
    "ma07_workload",
    "ma08_crash_injection",
    "ma09_active_delegation",
    "evaluator_metrics",
    "output_digest",
)


class WorkloadEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = build_evidence()

    def test_schema_keys_present(self):
        for key in TOP_LEVEL_KEYS:
            self.assertIn(key, self.evidence)
        self.assertEqual(self.evidence["schema_version"], SCHEMA_VERSION)
        self.assertEqual(self.evidence["claim_boundary"], CLAIM_BOUNDARY)

    def test_ma07_injected_task_recovered(self):
        ma07 = self.evidence["ma07_workload"]
        self.assertEqual(ma07["status"], "passed")
        self.assertTrue(ma07["recovery_assertion"]["asserted"])
        clean = ma07["clean_run"]
        crash = ma07["crash_run"]
        self.assertEqual(clean["statuses"], ["passed", "passed", "passed"])
        self.assertEqual(clean["attempts"], [1, 1, 1])
        self.assertEqual(clean["recovered_tasks"], [])
        self.assertEqual(crash["statuses"], ["passed", "passed", "passed"])
        self.assertIn("crash-task-b", crash["recovered_tasks"])
        ordered = sorted(["crash-task-a", "crash-task-b", "crash-task-c"])
        injected_index = ordered.index("crash-task-b")
        self.assertEqual(crash["attempts"][injected_index], 2)
        self.assertNotEqual(clean["aggregate_digest"], crash["aggregate_digest"])

    def test_ma08_summaries_shape_and_determinism_inputs(self):
        section = self.evidence["ma08_crash_injection"]
        self.assertEqual(section["prober"], "CrashInjectionProber")
        self.assertEqual(section["repetitions"], 10)
        self.assertEqual(section["seed"], 20260825)
        summaries = section["summaries"]
        self.assertEqual(len(summaries), 5)
        expected_phases = {"pre_write", "post_write", "pre_read", "post_read", "workspace_escape"}
        self.assertEqual({row["phase"] for row in summaries}, expected_phases)
        for row in summaries:
            self.assertEqual(row["runs"], 10)
            self.assertGreaterEqual(row["survival_rate"], 0.0)
            self.assertLessEqual(row["survival_rate"], 1.0)
            self.assertLessEqual(row["min_ms"], row["p50_ms"])
            self.assertLessEqual(row["p50_ms"], row["p95_ms"])
            self.assertLessEqual(row["p95_ms"], row["max_ms"])

    def test_ma09_all_probes_passed(self):
        ma09 = self.evidence["ma09_active_delegation"]
        self.assertTrue(ma09["all_passed"])
        self.assertEqual(len(ma09["results"]), 4)
        for row in ma09["results"]:
            self.assertTrue(row["passed"])
            self.assertTrue(str(row["observed"]).startswith("denied:"))

    def test_evaluator_metrics_match_fixture(self):
        metrics = self.evidence["evaluator_metrics"]
        self.assertEqual(metrics["cases"], len(EVALUATOR_OUTCOMES))
        self.assertEqual(metrics["cases"], 6)
        self.assertAlmostEqual(metrics["correctness_rate"], 5.0 / 6.0, places=12)
        self.assertAlmostEqual(metrics["delivery_rate"], 5.0 / 6.0, places=12)
        self.assertEqual(metrics["leakage_free_rate"], 1.0)
        self.assertAlmostEqual(metrics["recovery_rate"], 1.0 / 3.0, places=12)
        self.assertAlmostEqual(metrics["review_approval_rate"], 4.0 / 6.0, places=12)
        self.assertAlmostEqual(metrics["commit_rate"], 5.0 / 6.0, places=12)
        self.assertAlmostEqual(metrics["retry_rate"], 1.0 / 3.0, places=12)
        self.assertAlmostEqual(metrics["work_product_score"], 27.0 / 36.0, places=12)

    def test_output_digest_covers_payload_and_is_stable_across_builds(self):
        first = dict(self.evidence)
        second = build_evidence()
        payload_first = {key: value for key, value in first.items() if key != "output_digest"}
        payload_second = {key: value for key, value in second.items() if key != "output_digest"}
        self.assertEqual(
            json.dumps(payload_first, sort_keys=True),
            json.dumps(payload_second, sort_keys=True),
        )
        self.assertEqual(first["output_digest"], second["output_digest"])
        self.assertEqual(first["output_digest"], canonical_digest(payload_second))

    def test_no_timestamp_like_keys_or_values_anywhere(self):
        serialized = json.dumps(self.evidence, ensure_ascii=False, sort_keys=True)
        matches = TIMESTAMP_PATTERN.findall(serialized)
        self.assertEqual(matches, [])
        for key in self.evidence:
            self.assertIsNone(TIMESTAMP_PATTERN.search(key))


if __name__ == "__main__":
    unittest.main(verbosity=2)
