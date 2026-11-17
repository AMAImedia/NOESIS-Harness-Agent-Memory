"""Seeded adversarial corpus v3 tests: determinism, seed sensitivity, fail-closed edges."""
import tempfile
import unittest
from pathlib import Path

from noesis_harness import Memory
from noesis_harness.memory_quality import DurableMemoryQualityAdapter, DurableMemoryQualityTraceStore
from noesis_harness.memory_quality_corpora_v3 import (
    CATEGORIES_V3,
    CORPUS_SCHEMA_VERSION_V3,
    DEFAULT_CASES_PER_CATEGORY_V3,
    DEFAULT_SEED_V3,
    MemoryQualityCorpusError,
    evaluate_corpus_v3,
    expected_metrics_v3,
    generate_corpus_v3,
)


def _adapter_factory(tmp):
    def make():
        memory = Memory(str(Path(tmp) / "memory.db"))
        store = DurableMemoryQualityTraceStore(str(Path(tmp) / "quality.db"))
        return DurableMemoryQualityAdapter(memory, store)

    return make


class GenerateCorpusV3Tests(unittest.TestCase):
    def test_same_seed_reproduces_identical_payloads(self):
        corpus_one = generate_corpus_v3(DEFAULT_SEED_V3)
        corpus_two = generate_corpus_v3(DEFAULT_SEED_V3)
        self.assertEqual([case.payload() for case in corpus_one], [case.payload() for case in corpus_two])
        self.assertEqual([case.provenance_digest() for case in corpus_one], [case.provenance_digest() for case in corpus_two])

    def test_different_seed_changes_case_ids_and_corpus_content(self):
        base = generate_corpus_v3(12345)
        other = generate_corpus_v3(12346)
        base_ids = {case.case_id for case in base}
        other_ids = {case.case_id for case in other}
        self.assertEqual(base_ids & other_ids, set())
        self.assertNotEqual(
            [case.payload() for case in base],
            [case.payload() for case in other],
        )

    def test_size_categories_and_unique_ids(self):
        cases_per_category = DEFAULT_CASES_PER_CATEGORY_V3
        corpus = generate_corpus_v3(DEFAULT_SEED_V3)
        self.assertEqual(len(corpus), 8 * cases_per_category)
        ids = [case.case_id for case in corpus]
        self.assertEqual(len(ids), len(set(ids)))
        categories = {case.category for case in corpus}
        self.assertEqual(categories, set(CATEGORIES_V3))
        counts = {category: sum(1 for case in corpus if case.category == category) for category in CATEGORIES_V3}
        self.assertEqual(sorted(counts.values()), [cases_per_category] * 8)

    def test_expectation_table_covers_every_case(self):
        corpus = generate_corpus_v3(DEFAULT_SEED_V3)
        for case in corpus:
            entry = expected_metrics_v3(case)
            self.assertTrue(entry)
            self.assertTrue(case.case_id.startswith("v3-c%s-" % DEFAULT_SEED_V3))

    def test_parameter_validation_fails_closed(self):
        with self.assertRaisesRegex(MemoryQualityCorpusError, "seed_invalid"):
            generate_corpus_v3(seed="8675309")
        with self.assertRaisesRegex(MemoryQualityCorpusError, "cases_per_category_out_of_range"):
            generate_corpus_v3(cases_per_category=0)
        with self.assertRaisesRegex(MemoryQualityCorpusError, "cases_per_category_out_of_range"):
            generate_corpus_v3(cases_per_category=17)


class EvaluateCorpusV3Tests(unittest.TestCase):
    def test_same_seed_byte_equality_across_two_temp_dirs(self):
        with tempfile.TemporaryDirectory() as tmp_a, tempfile.TemporaryDirectory() as tmp_b:
            report_one = evaluate_corpus_v3(_adapter_factory(tmp_a))
            report_two = evaluate_corpus_v3(_adapter_factory(tmp_b))
            self.assertEqual(report_one["schema_version"], CORPUS_SCHEMA_VERSION_V3)
            self.assertEqual(report_one, report_two)
            self.assertEqual(report_one["report_digest"], report_two["report_digest"])
            self.assertEqual(report_one["corpus_digest"], report_two["corpus_digest"])
            self.assertEqual(len(report_one["per_case"]), 8 * DEFAULT_CASES_PER_CATEGORY_V3)
            violations = {
                case_id: entry["expectation_violations"]
                for case_id, entry in report_one["per_case"].items()
                if entry["expectation_violations"]
            }
            self.assertEqual(violations, {})
            self.assertFalse(report_one["duplicate_attribution_inflation_detected"])
            self.assertTrue(all(entry["provenance_verified"] for entry in report_one["per_case"].values()))

    def test_different_seed_changes_report_and_corpus_digests(self):
        with tempfile.TemporaryDirectory() as tmp_a, tempfile.TemporaryDirectory() as tmp_b:
            report_base = evaluate_corpus_v3(_adapter_factory(tmp_a), seed=424242)
            report_other = evaluate_corpus_v3(_adapter_factory(tmp_b), seed=424243)
            self.assertNotEqual(report_base["corpus_digest"], report_other["corpus_digest"])
            self.assertNotEqual(report_base["report_digest"], report_other["report_digest"])
            self.assertEqual(report_base["seed"], 424242)
            self.assertEqual(report_other["seed"], 424243)

    def test_temporal_inversion_detection_located_dynamically_by_category(self):
        corpus = generate_corpus_v3(DEFAULT_SEED_V3)
        members = [case for case in corpus if case.category == "temporal_inversion_pair"]
        self.assertTrue(members)
        flags = {case.temporal_order_correct for case in members}
        self.assertIn(True, flags)
        self.assertIn(False, flags)
        with tempfile.TemporaryDirectory() as tmp:
            report = evaluate_corpus_v3(_adapter_factory(tmp))
            per_case = report["per_case"]
            detected_true = next(case for case in members if case.temporal_order_correct)
            detected_false = next(case for case in members if not case.temporal_order_correct)
            self.assertEqual(per_case[detected_true.case_id]["temporal_order"], 1.0)
            self.assertEqual(per_case[detected_false.case_id]["temporal_order"], 0.0)
            total = len(corpus)
            inverted = sum(1 for case in members if not case.temporal_order_correct)
            expected_rate = (total - inverted) / float(total)
            self.assertEqual(report["aggregate"]["temporal_order_rate"], expected_rate)

    def test_decay_leakage_budget_and_reuse_edges_fail_visible_or_not_at_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = evaluate_corpus_v3(_adapter_factory(tmp), seed=777)
            per_case = report["per_case"]
            decay_entries = [entry for entry in per_case.values() if entry["category"] == "decay_floor_boundary"]
            self.assertTrue(decay_entries)
            for entry in decay_entries:
                self.assertTrue(entry["decay_floor_boundary_respected"])
                self.assertEqual(entry["compaction_retention"], 0.5)
                self.assertEqual(entry["expectation_violations"], [])
            leak_flags = {entry["leakage_free"] for entry in per_case.values() if entry["category"] == "leakage_decoy"}
            self.assertIn(False, leak_flags)
            reuse_values = {entry["experience_reuse_recall"] for entry in per_case.values() if entry["category"] == "cross_session_decoy_reuse"}
            self.assertEqual(reuse_values, {0.0, 1.0})
            budget_entries = [entry for entry in per_case.values() if entry["category"] == "budget_edge_long_trace"]
            self.assertEqual({entry["budget_respected"] for entry in budget_entries}, {True, False})
            sessions = set(report["session_ids"])
            beta_sessions = {session for session in sessions if session.endswith("session-beta")}
            self.assertEqual(len(beta_sessions), 1)

    def test_custom_cases_per_category_stays_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp_a, tempfile.TemporaryDirectory() as tmp_b:
            report_one = evaluate_corpus_v3(_adapter_factory(tmp_a), cases_per_category=1)
            report_two = evaluate_corpus_v3(_adapter_factory(tmp_b), cases_per_category=1)
            self.assertEqual(report_one, report_two)
            self.assertEqual(report_one["corpus_size"], 8)
            self.assertEqual(len(report_one["per_case"]), 8)

    def test_adapter_contract_violations_fail_closed(self):
        with self.assertRaisesRegex(MemoryQualityCorpusError, "adapter_factory_invalid"):
            evaluate_corpus_v3("not-callable")

        def missing_evaluate_sessions():
            return type("BrokenAdapter", (), {"record_trajectory": lambda self, *args: None})()

        with self.assertRaisesRegex(MemoryQualityCorpusError, "adapter_contract_invalid"):
            evaluate_corpus_v3(missing_evaluate_sessions)

        def non_callable_record():
            return type("BrokenAdapter", (), {"record_trajectory": None, "evaluate_sessions": lambda self, *args: None})()

        with self.assertRaisesRegex(MemoryQualityCorpusError, "adapter_contract_invalid"):
            evaluate_corpus_v3(non_callable_record)


if __name__ == "__main__":
    unittest.main()
