"""Tests for the committed evidence registry and its chain-surface wiring.

The registered artifacts are verified against the real committed repository
documents; negatives use tampered temp copies so committed files are never
modified. Conventions follow the sibling evidence-script tests.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.committed_evidence_registry import (
    COMMITTED_EVIDENCE_ARTIFACTS,
    REGISTERED_FILENAMES,
    RELEASE_AUDIT_EVIDENCE_PATH,
    STRUCTURAL_ONLY_REASON,
    WORKLOAD_EVIDENCE_PATH,
    verify_committed_evidence,
)
from scripts.run_workload_evidence import canonical_digest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _temp_copy(relative_path: str, mutate=None) -> Path:
    directory = Path(tempfile.mkdtemp(prefix="noesis-registry-"))
    target = directory / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    document = json.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8"))
    if mutate is not None:
        document = mutate(document)
    target.write_text(json.dumps(document, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return directory


class CommittedEvidenceRegistryTests(unittest.TestCase):
    def test_registry_pins_two_newest_artifacts_with_explicit_methods(self):
        self.assertEqual([str(entry["artifact_id"]) for entry in COMMITTED_EVIDENCE_ARTIFACTS], ["workload-evidence", "release-audit-evidence"])
        methods = {str(entry["artifact_id"]): str(entry["verification_method"]) for entry in COMMITTED_EVIDENCE_ARTIFACTS}
        self.assertEqual(methods["workload-evidence"], "recomputed_output_digest")
        self.assertEqual(methods["release-audit-evidence"], "structural_check_only")
        audit_entry = COMMITTED_EVIDENCE_ARTIFACTS[1]
        self.assertEqual(str(audit_entry["reason"]), STRUCTURAL_ONLY_REASON)
        self.assertEqual(REGISTERED_FILENAMES, {"MULTI_AGENT_WORKLOAD_EVIDENCE.json", "PARALLEL_RELEASE_AUDIT_EVIDENCE.json"})

    def test_real_committed_artifacts_verify_passed(self):
        result = verify_committed_evidence(REPO_ROOT)
        self.assertEqual(result["status"], "passed")
        workload = result["artifacts"]["workload-evidence"]
        committed = json.loads((REPO_ROOT / WORKLOAD_EVIDENCE_PATH).read_text(encoding="utf-8"))
        self.assertEqual(workload["output_digest"], committed["output_digest"])
        self.assertEqual(workload["output_digest"], canonical_digest({key: value for key, value in committed.items() if key != "output_digest"}))
        audit = result["artifacts"]["release-audit-evidence"]
        self.assertEqual(audit["status"], "passed")
        self.assertEqual(audit["reason"], STRUCTURAL_ONLY_REASON)

    def test_tampered_workload_copy_is_blocked(self):
        def bump(document):
            document["evaluator_metrics"] = dict(document["evaluator_metrics"], cases=7)
            return document

        directory = Path(tempfile.mkdtemp(prefix="noesis-registry-tamper-"))
        target = directory / WORKLOAD_EVIDENCE_PATH
        target.parent.mkdir(parents=True, exist_ok=True)
        committed = json.loads((REPO_ROOT / WORKLOAD_EVIDENCE_PATH).read_text(encoding="utf-8"))
        tampered = dict(committed)
        tampered["evaluator_metrics"] = dict(tampered["evaluator_metrics"], cases=7)
        target.write_text(json.dumps(tampered, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        result = verify_committed_evidence(directory)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["artifacts"]["workload-evidence"]["reason"], "workload_output_digest_mismatch")
        shutil.rmtree(directory)

    def test_structural_drift_in_release_audit_copy_is_blocked(self):
        cases = {
            "workspace_count_mismatch": lambda doc: dict(doc, workspace_count=4),
            "results_count_mismatch": lambda doc: dict(doc, results=doc["results"][:-1]),
            "release_audit_lane_not_passed": lambda doc: dict(doc, results=[dict(item, status="blocked") if index == 0 else item for index, item in enumerate(doc["results"])]),
            "release_audit_schema_mismatch": lambda doc: dict(doc, schema_version="noesis.parallel-release-audit.v2"),
        }
        for expected_reason, mutate in cases.items():
            directory = _temp_copy(RELEASE_AUDIT_EVIDENCE_PATH, mutate)
            result = verify_committed_evidence(directory)
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["artifacts"]["release-audit-evidence"]["reason"], expected_reason)
            self.assertEqual(result["artifacts"]["release-audit-evidence"]["entry_reason"], STRUCTURAL_ONLY_REASON)
            shutil.rmtree(directory)

    def test_missing_and_invalid_files_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            result = verify_committed_evidence(directory)
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["artifacts"]["workload-evidence"]["reason"], "artifact_missing")
            self.assertEqual(result["artifacts"]["release-audit-evidence"]["reason"], "artifact_missing")
        directory = _temp_copy(WORKLOAD_EVIDENCE_PATH)
        (directory / WORKLOAD_EVIDENCE_PATH).write_text("{not-json", encoding="utf-8")
        result = verify_committed_evidence(directory)
        self.assertEqual(result["artifacts"]["workload-evidence"]["reason"], "artifact_json_invalid")
        shutil.rmtree(directory)

    def test_absent_entries_do_not_block_when_not_required(self):
        with tempfile.TemporaryDirectory() as directory:
            result = verify_committed_evidence(directory, require_all=False)
            self.assertEqual(result["status"], "absent")
            statuses = {item["status"] for item in result["artifacts"].values()}
            self.assertEqual(statuses, {"absent"})

    def test_partial_presence_blocks_when_one_present_entry_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / WORKLOAD_EVIDENCE_PATH).parent.mkdir(parents=True, exist_ok=True)
            broken = Path(tempfile.mkdtemp(prefix="noesis-registry-src-")) / "broken.json"
            broken.write_text("{not-json", encoding="utf-8")
            shutil.copyfile(broken, root / WORKLOAD_EVIDENCE_PATH)
            result = verify_committed_evidence(root, require_all=False)
            self.assertEqual(result["status"], "blocked")
            shutil.rmtree(broken.parent)


if __name__ == "__main__":
    unittest.main(verbosity=2)
