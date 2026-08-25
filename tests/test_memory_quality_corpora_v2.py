"""Adversarial corpus v2 tests: determinism, detection, and fail-closed edges."""
import tempfile
import unittest
from pathlib import Path

from noesis_harness import Memory
from noesis_harness.memory_quality import DurableMemoryQualityAdapter, DurableMemoryQualityTraceStore
from noesis_harness.memory_quality_corpora import (
    ADVERSARIAL_CORPUS_V2,
    CORPUS_SCHEMA_VERSION,
    EXPECTED_V2,
    MemoryQualityCorpusError,
    evaluate_corpus_v2,
)


def _adapter_factory(tmp):
    def make():
        memory = Memory(str(Path(tmp) / "memory.db"))
        store = DurableMemoryQualityTraceStore(str(Path(tmp) / "quality.db"))
        return DurableMemoryQualityAdapter(memory, store)

    return make


class AdversarialCorpusV2Tests(unittest.TestCase):
    def test_corpus_size_and_unique_ids_and_schema(self):
        self.assertGreaterEqual(len(ADVERSARIAL_CORPUS_V2), 8)
        ids = [case.case_id for case in ADVERSARIAL_CORPUS_V2]
        self.assertEqual(len(ids), len(set(ids)))
        categories = {case.category for case in ADVERSARIAL_CORPUS_V2}
        for required in (
            "temporal_inversion_pair",
            "duplicate_attribution",
            "near_duplicate_query",
            "budget_edge_long_trace",
            "cross_session_decoy_reuse",
            "conflict_with_provenance",
            "decay_floor_boundary",
            "leakage_decoy",
        ):
            self.assertIn(required, categories)
        self.assertEqual(EXPECTED_V2.keys(), set(ids))

    def test_aggregate_determinism_across_two_evaluations(self):
        with tempfile.TemporaryDirectory() as tmp_a, tempfile.TemporaryDirectory() as tmp_b:
            report_one = evaluate_corpus_v2(_adapter_factory(tmp_a))
            report_two = evaluate_corpus_v2(_adapter_factory(tmp_b))
            self.assertEqual(report_one["schema_version"], CORPUS_SCHEMA_VERSION)
            self.assertEqual(report_one, report_two)
            self.assertEqual(report_one["report_digest"], report_two["report_digest"])
            self.assertEqual(len(report_one["per_case"]), len(ADVERSARIAL_CORPUS_V2))
            violations = {case_id: entry["expectation_violations"] for case_id, entry in report_one["per_case"].items() if entry["expectation_violations"]}
            self.assertEqual(violations, {})
            self.assertFalse(report_one["duplicate_attribution_inflation_detected"])

    def test_temporal_inversion_pair_detected_correctly(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = evaluate_corpus_v2(_adapter_factory(tmp))
            per_case = report["per_case"]
            self.assertEqual(per_case["v2-temporal-inversion-early"]["temporal_order"], 1.0)
            self.assertEqual(per_case["v2-temporal-inversion-late"]["temporal_order"], 0.0)
            expected_rate = (len(ADVERSARIAL_CORPUS_V2) - 1) / float(len(ADVERSARIAL_CORPUS_V2))
            self.assertEqual(report["aggregate"]["temporal_order_rate"], expected_rate)
            self.assertEqual(per_case["v2-temporal-inversion-late"]["recall"], 1.0)
            self.assertEqual(per_case["v2-temporal-inversion-early"]["session_id"], per_case["v2-temporal-inversion-late"]["session_id"])

    def test_duplicate_attribution_does_not_inflate_precision(self):
        case = next(case for case in ADVERSARIAL_CORPUS_V2 if case.case_id == "v2-duplicate-attribution")
        self.assertEqual(case.attributed_source_ids.count("v2-src-dup"), 2)
        with tempfile.TemporaryDirectory() as tmp:
            report = evaluate_corpus_v2(_adapter_factory(tmp))
            precision = report["per_case"]["v2-duplicate-attribution"]["attribution_precision"]
            attributed_set = set(case.attributed_source_ids)
            relevant_set = set(case.relevant_source_ids)
            honest_precision = len(attributed_set & relevant_set) / float(len(attributed_set))
            self.assertEqual(precision, honest_precision)
            self.assertEqual(precision, 0.5)
            self.assertEqual(report["aggregate"]["attribution_precision_mean"], (len(ADVERSARIAL_CORPUS_V2) - 1 + 0.5) / len(ADVERSARIAL_CORPUS_V2))

    def test_budget_edge_complies_hard_budget_or_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = evaluate_corpus_v2(_adapter_factory(tmp))
            per_case = report["per_case"]
            exact = per_case["v2-budget-edge-exact"]
            overrun = per_case["v2-budget-edge-overrun"]
            self.assertTrue(exact["budget_respected"])
            self.assertEqual(exact["expectation_violations"], [])
            self.assertFalse(overrun["budget_respected"])
            self.assertEqual(overrun["expectation_violations"], [])
            expected_rate = (len(ADVERSARIAL_CORPUS_V2) - 1) / float(len(ADVERSARIAL_CORPUS_V2))
            self.assertEqual(report["aggregate"]["budget_compliance_rate"], expected_rate)
            edge_cases = [case for case in ADVERSARIAL_CORPUS_V2 if case.category == "budget_edge_long_trace"]
            self.assertEqual(sorted(case.used_tokens - case.budget_tokens for case in edge_cases), [0, 1])

    def test_provenance_decay_leakage_and_cross_session_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = evaluate_corpus_v2(_adapter_factory(tmp))
            per_case = report["per_case"]
            self.assertTrue(all(entry["provenance_verified"] for entry in per_case.values()))
            decay = per_case["v2-decay-floor-boundary"]
            self.assertTrue(decay["decay_floor_boundary_respected"])
            self.assertEqual(decay["compaction_retention"], 0.5)
            conflict = per_case["v2-conflict-provenance"]
            self.assertEqual(conflict["conflict_resolution"], 0.0)
            self.assertTrue(conflict["provenance_verified"])
            self.assertFalse(per_case["v2-leakage-decoy"]["leakage_free"])
            self.assertEqual(per_case["v2-leakage-decoy"]["attribution_precision"], 1.0)
            beta_sessions = {case.session_id for case in ADVERSARIAL_CORPUS_V2 if case.case_id.startswith("v2-cross-session")}
            self.assertNotIn(per_case["v2-budget-edge-exact"]["session_id"], beta_sessions)
            self.assertEqual(per_case["v2-cross-session-decoy-beta"]["experience_reuse_recall"], 0.0)
            self.assertEqual(report["aggregate"]["leakage_free_rate"], (len(ADVERSARIAL_CORPUS_V2) - 1) / float(len(ADVERSARIAL_CORPUS_V2)))

    def test_invalid_adapter_factories_fail_closed(self):
        with self.assertRaisesRegex(MemoryQualityCorpusError, "adapter_factory_invalid"):
            evaluate_corpus_v2("not-callable")

        def empty_adapter():
            return type("BrokenAdapter", (), {"record_trajectory": None})()

        with self.assertRaisesRegex(MemoryQualityCorpusError, "adapter_contract_invalid"):
            evaluate_corpus_v2(empty_adapter)


if __name__ == "__main__":
    unittest.main()
