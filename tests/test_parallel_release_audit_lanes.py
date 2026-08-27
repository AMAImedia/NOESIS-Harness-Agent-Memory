"""Tests for the offline parallel release-audit lanes runner.

Follows the sibling evidence-script test conventions: the runner entry point
is invoked directly (no subprocess), and single-lane callbacks are exercised
against an injected AgentLaneContext. The workload-evidence-audit lane is
verified against the committed Gate 4 artifact plus tampered temp copies;
the repo-path constant is patched per-test so the real docs file is never
modified.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from noesis_harness.parallel_agent import AgentLaneContext
from scripts.run_parallel_release_audit_lanes import (
    WORKLOAD_EVIDENCE_SCHEMA,
    WORKLOAD_EVIDENCE_PATH,
    lane,
    main,
)
from scripts.run_workload_evidence import canonical_digest


EXPECTED_TASK_IDS = ("doc-checklist", "git-integrity", "package-exports", "secret-ast-audit", "workload-evidence-audit")


def _context(task_id: str) -> AgentLaneContext:
    return AgentLaneContext("release-audit-session", task_id, "audit-" + task_id, Path(tempfile.gettempdir()), frozenset())


class ParallelReleaseAuditLanesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.committed = json.loads(WORKLOAD_EVIDENCE_PATH.read_text(encoding="utf-8"))

    def test_main_runs_five_lanes_all_passed_in_task_id_order(self):
        with tempfile.TemporaryDirectory(prefix="noesis-release-audit-check-") as directory:
            output = Path(directory) / "report.json"
            exit_code = main(["--output", str(output)])
            self.assertEqual(exit_code, 0)
            report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report["schema_version"], "noesis.parallel-release-audit.v1")
        self.assertEqual(report["mode"], "offline")
        task_ids = tuple(item["task_id"] for item in report["results"])
        self.assertEqual(task_ids, EXPECTED_TASK_IDS)
        self.assertEqual([item["status"] for item in report["results"]], ["passed"] * len(EXPECTED_TASK_IDS))
        self.assertEqual(len({item["workspace"] for item in report["results"]}), len(EXPECTED_TASK_IDS))
        self.assertEqual(report["workspace_count"], len(EXPECTED_TASK_IDS))
        self.assertIn("lane_started", report["event_kinds"])
        self.assertIn("lane_completed", report["event_kinds"])
        workload = next(item for item in report["results"] if item["task_id"] == "workload-evidence-audit")
        self.assertEqual(workload["output"]["schema_version"], WORKLOAD_EVIDENCE_SCHEMA)
        self.assertEqual(workload["output"]["output_digest"], self.committed["output_digest"])

    def test_workload_lane_passes_on_committed_artifact(self):
        result = lane(_context("workload-evidence-audit"))
        self.assertEqual(result["check"], "workload_evidence_audit")
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["schema_version"], WORKLOAD_EVIDENCE_SCHEMA)
        self.assertEqual(result["output_digest"], self.committed["output_digest"])
        self.assertEqual(result["output_digest"], canonical_digest({key: value for key, value in self.committed.items() if key != "output_digest"}))

    def test_workload_lane_rejects_tampered_payload(self):
        with tempfile.TemporaryDirectory(prefix="noesis-release-audit-tamper-") as directory:
            copy = Path(directory) / "MULTI_AGENT_WORKLOAD_EVIDENCE.json"
            tampered = dict(self.committed)
            tampered["evaluator_metrics"] = dict(tampered["evaluator_metrics"], cases=7)
            copy.write_text(json.dumps(tampered, ensure_ascii=False, sort_keys=True), encoding="utf-8")
            with patch("scripts.run_parallel_release_audit_lanes.WORKLOAD_EVIDENCE_PATH", copy):
                with self.assertRaises(AssertionError) as raised:
                    lane(_context("workload-evidence-audit"))
            self.assertIn("workload_digest_mismatch", str(raised.exception))

    def test_workload_lane_rejects_schema_mismatch(self):
        with tempfile.TemporaryDirectory(prefix="noesis-release-audit-schema-") as directory:
            copy = Path(directory) / "MULTI_AGENT_WORKLOAD_EVIDENCE.json"
            tampered = {key: value for key, value in self.committed.items() if key != "output_digest"}
            tampered["schema_version"] = "noesis.workload-evidence.v2"
            tampered["output_digest"] = canonical_digest(tampered)
            copy.write_text(json.dumps(tampered, ensure_ascii=False, sort_keys=True), encoding="utf-8")
            with patch("scripts.run_parallel_release_audit_lanes.WORKLOAD_EVIDENCE_PATH", copy):
                with self.assertRaises(AssertionError) as raised:
                    lane(_context("workload-evidence-audit"))
            message = str(raised.exception)
            self.assertIn("workload_schema_mismatch", message)
            self.assertNotIn("workload_digest_mismatch", message)

    def test_workload_lane_rejects_missing_artifact(self):
        with tempfile.TemporaryDirectory(prefix="noesis-release-audit-missing-") as directory:
            missing = Path(directory) / "absent.json"
            with patch("scripts.run_parallel_release_audit_lanes.WORKLOAD_EVIDENCE_PATH", missing):
                with self.assertRaises(AssertionError) as raised:
                    lane(_context("workload-evidence-audit"))
            self.assertIn("workload_evidence_missing", str(raised.exception))

    def test_workload_lane_rejects_invalid_json(self):
        with tempfile.TemporaryDirectory(prefix="noesis-release-audit-broken-") as directory:
            broken = Path(directory) / "broken.json"
            broken.write_text("{not-json", encoding="utf-8")
            with patch("scripts.run_parallel_release_audit_lanes.WORKLOAD_EVIDENCE_PATH", broken):
                with self.assertRaises(AssertionError) as raised:
                    lane(_context("workload-evidence-audit"))
            self.assertIn("workload_evidence_invalid_json", str(raised.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
