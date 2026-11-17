import unittest

from scripts.build_operator_case_bundle import build_bundle


class OperatorCaseBundleTests(unittest.TestCase):
    def base(self):
        return {
            "schema_version": "noesis.external-runner-manifest.v1",
            "revisions": {"hermes": "h1", "opencode": "o1", "deepseek_harness": "d1"},
            "case_ids": ["case-a", "case-b"],
            "network_policy": "deny",
            "credentials": "absent",
            "workspace_mode": "disposable",
            "protocol_fingerprint": "a" * 64,
        }

    def test_complete_manifest_is_readiness_only(self):
        bundle = build_bundle(self.base())
        self.assertEqual(bundle["status"], "ready_for_operator_preflight")
        self.assertFalse(bundle["execution_allowed"])
        self.assertFalse(bundle["automatic_execution"])
        self.assertTrue(bundle["approval_required"])
        self.assertFalse(bundle["external_execution_claim"])

    def test_missing_revision_is_not_run_not_executed(self):
        manifest = self.base()
        manifest["revisions"]["hermes"] = ""
        bundle = build_bundle(manifest)
        self.assertEqual(bundle["status"], "not_run")
        self.assertEqual(bundle["lane_status"]["hermes"], "not_run")
        self.assertFalse(bundle["execution_allowed"])

    def test_unsafe_policy_is_blocked(self):
        manifest = self.base()
        manifest["network_policy"] = "allow"
        bundle = build_bundle(manifest)
        self.assertEqual(bundle["status"], "blocked")
        self.assertIn("network_must_be_deny", bundle["errors"])
        self.assertFalse(bundle["execution_allowed"])

    def test_duplicate_case_ids_are_blocked(self):
        manifest = self.base()
        manifest["case_ids"] = ["case-a", "case-a"]
        bundle = build_bundle(manifest)
        self.assertEqual(bundle["status"], "blocked")
        self.assertIn("duplicate_case_id", bundle["errors"])


if __name__ == "__main__":
    unittest.main()
