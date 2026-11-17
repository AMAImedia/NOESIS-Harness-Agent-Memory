import json
import tempfile
import unittest
from pathlib import Path

from noesis_harness import project_evidence
from noesis_harness.evidence_projection import load_memory_quality_digests, load_workload_evidence
from noesis_harness.health_server import HealthServer


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKLOAD_EVIDENCE_PATH = REPO_ROOT / "docs" / "MULTI_AGENT_WORKLOAD_EVIDENCE.json"
MEMORY_QUALITY_EVIDENCE_PATH = REPO_ROOT / "docs" / "MEMORY_QUALITY_EVIDENCE.json"


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


class Gate1EvidenceProjectionTests(unittest.TestCase):
    def test_real_workload_evidence_verifies(self):
        result = load_workload_evidence(WORKLOAD_EVIDENCE_PATH)
        self.assertTrue(result["available"])
        self.assertTrue(result["digest_verified"])
        self.assertEqual(result["schema_version"], "noesis.workload-evidence.v1")
        self.assertTrue(result["output_digest"].startswith("sha256:"))
        self.assertEqual(result["reason"], "")

    def test_tampered_workload_copy_fails_closed(self):
        raw = WORKLOAD_EVIDENCE_PATH.read_bytes()
        marker = raw.index(b'"output_digest"')
        hex_start = raw.index(b'sha256:', marker) + len(b'sha256:')
        tampered = raw[:hex_start] + bytes([raw[hex_start] ^ 0x01]) + raw[hex_start + 1:]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tampered.json"
            path.write_bytes(tampered)
            result = load_workload_evidence(path)
        self.assertTrue(result["available"])
        self.assertFalse(result["digest_verified"])
        self.assertEqual(result["reason"], "output_digest_mismatch")

    def test_missing_and_corrupt_files_fail_closed(self):
        missing = load_workload_evidence(REPO_ROOT / "docs" / "NO_SUCH_WORKLOAD_EVIDENCE.json")
        self.assertFalse(missing["available"])
        self.assertFalse(missing["digest_verified"])
        self.assertTrue(missing["reason"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "corrupt.json"
            path.write_bytes(b"{not json")
            corrupt = load_workload_evidence(path)
        self.assertFalse(corrupt["available"])
        self.assertFalse(corrupt["digest_verified"])
        self.assertEqual(corrupt["reason"], "json_invalid")

    def test_memory_quality_digest_entries(self):
        entries = load_memory_quality_digests(MEMORY_QUALITY_EVIDENCE_PATH)
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0]["corpus_schema_version"], "noesis.memory-quality-corpus.v2")
        self.assertTrue(entries[0]["report_digest"].startswith("sha256:"))
        self.assertTrue(entries[0]["digest_present"])
        self.assertEqual(entries[1]["corpus_schema_version"], "noesis.memory-quality-corpus.v3")
        self.assertTrue(entries[1]["digest_present"])
        self.assertEqual(entries[2]["corpus_schema_version"], "noesis.memory-quality-evidence.v3")
        self.assertFalse(entries[2]["digest_present"])
        self.assertEqual(load_memory_quality_digests(REPO_ROOT / "docs" / "NO_SUCH_FILE.json"), [])
        self.assertEqual(load_memory_quality_digests(None), [])

    def test_projection_is_deterministic_byte_equal(self):
        first = project_evidence(WORKLOAD_EVIDENCE_PATH, MEMORY_QUALITY_EVIDENCE_PATH)
        second = project_evidence(WORKLOAD_EVIDENCE_PATH, MEMORY_QUALITY_EVIDENCE_PATH)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        self.assertEqual(first["schema_version"], "noesis.evidence-projection.v1")
        self.assertTrue(first["workload_evidence"]["digest_verified"])
        self.assertEqual(len(first["memory_quality_digests"]), 3)

    def test_projection_defaults_are_safe(self):
        projection = project_evidence()
        self.assertEqual(projection["schema_version"], "noesis.evidence-projection.v1")
        self.assertFalse(projection["workload_evidence"]["available"])
        self.assertEqual(projection["workload_evidence"]["reason"], "path_not_provided")
        self.assertEqual(projection["memory_quality_digests"], [])

    def test_healthserver_default_snapshot_unchanged(self):
        snapshot = HealthServer().operator_snapshot()
        self.assertNotIn("evidence_projection", snapshot)

    def test_healthserver_includes_projection_when_provided(self):
        projection = project_evidence(WORKLOAD_EVIDENCE_PATH, MEMORY_QUALITY_EVIDENCE_PATH)
        snapshot = HealthServer().operator_snapshot(evidence_projection=projection)
        self.assertIn("evidence_projection", snapshot)
        self.assertEqual(snapshot["evidence_projection"], projection)


if __name__ == "__main__":
    unittest.main()
