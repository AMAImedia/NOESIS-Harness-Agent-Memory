import unittest

from noesis_harness.health_server import HealthServer
from noesis_harness.report_export_lifecycle import lifecycle_audit_readiness


class LifecycleAuditReadinessTests(unittest.TestCase):
    def test_missing_provider_is_not_run_and_never_satisfies_lanes(self):
        item = HealthServer().operator_snapshot()["lifecycle_audit_readiness"]
        self.assertEqual(item["status"], "not_run")
        self.assertFalse(item["execution_lane_satisfied"])
        self.assertFalse(item["native_lane_satisfied"])
        self.assertFalse(item["external_lane_satisfied"])
        self.assertFalse(item["comparative_claim"])

    def test_provider_is_forced_to_audit_only(self):
        server = HealthServer(lifecycle_audit_readiness_provider=lambda: {"status": "passed", "execution_lane_satisfied": True, "native_lane_satisfied": True, "external_lane_satisfied": True, "comparative_claim": True, "operator_token": "secret"})
        item = server.telemetry_snapshot()["lifecycle_audit_readiness"]
        self.assertEqual(item["status"], "passed")
        self.assertFalse(item["execution_lane_satisfied"])
        self.assertFalse(item["native_lane_satisfied"])
        self.assertFalse(item["external_lane_satisfied"])
        self.assertFalse(item["comparative_claim"])
        self.assertEqual(item["operator_token"], "[REDACTED]")

    def test_provider_failure_is_blocked(self):
        server = HealthServer(lifecycle_audit_readiness_provider=lambda: (_ for _ in ()).throw(RuntimeError("broken")))
        item = server.operator_snapshot()["lifecycle_audit_readiness"]
        self.assertEqual(item["status"], "blocked")
        self.assertEqual(item["claim_boundary"], "audit_only_lifecycle_evidence")


if __name__ == "__main__":
    unittest.main()
