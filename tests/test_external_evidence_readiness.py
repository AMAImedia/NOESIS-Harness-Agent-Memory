from __future__ import annotations

import unittest

from scripts.external_evidence_readiness import build_matrix
from scripts.external_runner_contract import make_spec
from scripts.ingest_runner_result import signature, ingest

KEY = "readiness-test-key-2026"


def evidence_for(system: str, revision: str, fingerprint_seed: str = "a") -> dict:
    spec = make_spec(system, revision, [system, "run", "--json"], "b" * 64)
    if fingerprint_seed != "a":
        spec["protocol_fingerprint"] = fingerprint_seed * 64
    result = {
        **spec,
        "execution": "completed",
        "status": "passed",
        "metrics": {"task_success": {"status": "observed", "value": 1.0}},
    }
    return ingest(spec, result, KEY)


def manifest(revisions: dict[str, str] | None = None, **extra) -> dict:
    return {"revisions": revisions or {"hermes": "h1", "opencode": "o1", "deepseek_harness": "d1"}, **extra}


class ExternalEvidenceReadinessTests(unittest.TestCase):
    def test_missing_lane_without_pin_is_not_run(self):
        report = build_matrix({"revisions": {}}, [], KEY)
        self.assertEqual(report["overall_status"], "not_run")
        self.assertEqual({lane["status"] for lane in report["lanes"].values()}, {"not_run"})

    def test_mismatched_revision_is_blocked(self):
        report = build_matrix(manifest(), [evidence_for("hermes", "other")], KEY)
        self.assertEqual(report["lanes"]["hermes"]["status"], "blocked")
        self.assertIn("revision_mismatch", report["lanes"]["hermes"]["checks"])

    def test_environment_digest_mismatch_is_blocked(self):
        record = evidence_for("hermes", "h1")
        report = build_matrix(manifest(environment_digests={"hermes": "0" * 64}), [record], KEY)
        self.assertEqual(report["lanes"]["hermes"]["status"], "blocked")
        self.assertIn("environment_digest_mismatch", report["lanes"]["hermes"]["checks"])

    def test_stale_receipt_is_blocked(self):
        record = dict(evidence_for("hermes", "h1"))
        record["receipt_id"] = "f" * 64
        record["signature"] = signature({key: value for key, value in record.items() if key != "signature"}, KEY)
        report = build_matrix(manifest(), [record], KEY)
        self.assertEqual(report["lanes"]["hermes"]["status"], "blocked")
        self.assertIn("stale_or_mismatched_receipt", report["lanes"]["hermes"]["checks"])

    def test_duplicate_system_record_is_blocked(self):
        first = evidence_for("hermes", "h1")
        second = evidence_for("hermes", "h1")
        report = build_matrix(manifest(), [first, second], KEY)
        self.assertEqual(report["lanes"]["hermes"]["status"], "blocked")
        self.assertEqual(report["lanes"]["hermes"]["reason"], "duplicate_system_record")

    def test_protocol_fingerprint_conflict_blocks_comparison(self):
        first = evidence_for("hermes", "h1", "a")
        second = evidence_for("opencode", "o1", "c")
        report = build_matrix(manifest(), [first, second], KEY)
        self.assertFalse(report["comparative_ready"])
        self.assertIn("protocol_fingerprint_conflict", report["global_checks"])
        self.assertEqual(report["overall_status"], "blocked")

    def test_unsupported_lane_is_explicit(self):
        record = dict(evidence_for("hermes", "h1"))
        record["status"] = "unsupported"
        record["signature"] = signature({key: value for key, value in record.items() if key != "signature"}, KEY)
        report = build_matrix(manifest(), [record], KEY)
        self.assertEqual(report["lanes"]["hermes"]["status"], "unsupported")


if __name__ == "__main__":
    unittest.main()
