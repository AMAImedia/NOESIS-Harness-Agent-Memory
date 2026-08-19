import unittest

from noesis_harness.health_server import HealthServer


class EvidenceProjectionTests(unittest.TestCase):
    def test_projection_is_bounded_read_only_and_claim_separated(self):
        server = HealthServer(evidence_aggregate_provider=lambda: {"schema_version": "noesis.signed-evidence-aggregate.v1", "status": "passed", "reason": "verified", "evidence_count": 2, "lanes": ["delegated", "child_runtime"], "aggregate_digest": "d" * 64, "comparative_claim": True, "execution_claim": True, "signing_key": "secret"})
        snapshot = server.operator_snapshot()
        aggregate = snapshot["evidence_aggregate"]
        self.assertEqual(aggregate["status"], "passed")
        self.assertFalse(aggregate["comparative_claim"])
        self.assertEqual(aggregate["claim_boundary"], "read_only_evidence_status")
        self.assertNotIn("signing_key", aggregate)
        self.assertEqual(server.telemetry_snapshot()["evidence_aggregate"]["execution_claim"], True)

    def test_provider_failure_is_blocked_without_claim(self):
        server = HealthServer(evidence_aggregate_provider=lambda: (_ for _ in ()).throw(RuntimeError("broken")))
        aggregate = server.telemetry_snapshot()["evidence_aggregate"]
        self.assertEqual(aggregate["status"], "blocked")
        self.assertFalse(aggregate["comparative_claim"])
        self.assertFalse(aggregate["execution_claim"])

    def test_unconfigured_provider_is_not_run(self):
        server = HealthServer()
        aggregate = server._evidence_aggregate_snapshot()
        self.assertEqual(aggregate["status"], "not_run")
        self.assertFalse(aggregate["execution_claim"])
        self.assertFalse(aggregate["comparative_claim"])


if __name__ == "__main__":
    unittest.main()
