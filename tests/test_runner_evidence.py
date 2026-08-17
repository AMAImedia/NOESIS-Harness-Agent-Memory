from __future__ import annotations

import unittest

from scripts.external_runner_contract import make_spec
from scripts.ingest_runner_result import ingest, verify_evidence


KEY = "local-test-evidence-key-2026"


class RunnerEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.spec = make_spec("hermes", "hermes-rev-1", ["hermes", "run", "--json"], "a" * 64)
        self.result = {
            **self.spec,
            "execution": "completed",
            "status": "not_run",
            "metrics": {
                "task_success": {"status": "not_run", "reason": "runner unavailable"},
                "credential_exposure": {"status": "not_run", "reason": "runner unavailable"},
            },
        }

    def test_valid_not_run_result_is_signed_and_verifiable(self):
        evidence = ingest(self.spec, self.result, KEY)
        self.assertTrue(evidence["accepted"])
        self.assertEqual(evidence["errors"], [])
        self.assertTrue(verify_evidence(evidence, KEY))
        self.assertFalse(verify_evidence(evidence, KEY + "-wrong"))
        self.assertNotIn(KEY, str(evidence))

    def test_revision_and_workspace_mismatch_fail_closed(self):
        tampered = {**self.result, "revision": "other-revision", "workspace": {"mode": "shared", "outside_access": "allow", "credentials": "absent"}}
        evidence = ingest(self.spec, tampered, KEY)
        self.assertFalse(evidence["accepted"])
        self.assertIn("identity_mismatch:revision", evidence["errors"])
        self.assertIn("workspace_mismatch", evidence["errors"])
        self.assertFalse(verify_evidence(evidence, KEY))

    def test_credential_like_result_is_rejected(self):
        tampered = {**self.result, "diagnostic": "token=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"}
        evidence = ingest(self.spec, tampered, KEY)
        self.assertFalse(evidence["accepted"])
        self.assertIn("credential_like_content", evidence["errors"])

    def test_metric_status_is_strict(self):
        tampered = {**self.result, "metrics": {"task_success": {"status": "maybe"}}}
        evidence = ingest(self.spec, tampered, KEY)
        self.assertFalse(evidence["accepted"])
        self.assertIn("invalid:metric:task_success", evidence["errors"])


if __name__ == "__main__":
    unittest.main()
