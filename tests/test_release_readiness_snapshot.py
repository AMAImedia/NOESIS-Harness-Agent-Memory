import unittest

from scripts.release_readiness_snapshot import build_snapshot, verify_snapshot


class ReleaseReadinessSnapshotTests(unittest.TestCase):
    audit_passed = {"status": "passed"}
    audit_blocked = {"status": "blocked"}

    def test_passed_local_readiness_with_honest_blockers(self):
        first = build_snapshot(self.audit_passed, 619, "3.14.7")
        second = build_snapshot(self.audit_passed, 619, "3.14.7")
        self.assertEqual(first, second)
        self.assertEqual(first["overall_status"], "passed")
        self.assertEqual(first["native_host_status"], "not_run")
        self.assertEqual(first["external_lanes_status"], "not_run")
        self.assertFalse(first["claims"]["native_execution"])
        self.assertFalse(first["claims"]["external_execution"])
        self.assertEqual(verify_snapshot(first)["status"], "passed")

    def test_blocked_audit_and_unsupported_claims(self):
        snapshot = build_snapshot(self.audit_blocked, 619, "3.14.7", native_status="unsupported", external_status="blocked")
        self.assertEqual(snapshot["overall_status"], "blocked")
        self.assertIn("matching_native_windows_macos_hosts_required", snapshot["blockers"])
        self.assertIn("pinned_external_lane_receipts_required", snapshot["blockers"])
        self.assertEqual(verify_snapshot(snapshot)["status"], "passed")

    def test_tamper_and_claim_boundary_are_rejected(self):
        snapshot = build_snapshot(self.audit_passed, 619, "3.14.7")
        tampered = dict(snapshot)
        tampered["validated_test_count"] = 620
        self.assertEqual(verify_snapshot(tampered)["reason"], "readiness_snapshot_digest_mismatch")
        claim = dict(snapshot)
        claim["claims"] = dict(snapshot["claims"])
        claim["claims"]["native_execution"] = True
        self.assertEqual(verify_snapshot(claim)["reason"], "readiness_snapshot_digest_mismatch")


if __name__ == "__main__":
    unittest.main()
