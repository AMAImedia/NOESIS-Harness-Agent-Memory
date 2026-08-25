"""End-to-end evidence projection transport surfaces.

Verifies that the fail-closed evidence projection (noesis.evidence-projection.v1,
patterns adapted from agentmemory fail-closed status surfaces) survives its two
operator-plane transports unchanged: the loopback HealthServer
/api/operator/snapshot endpoint over a real socket, and the ui_contract envelope
redaction/validation pass. Request patterns follow tests/test_ui_contract_health.py;
tamper fixtures follow tests/test_evidence_projection.py. The projection is built
by the caller per docs/EVIDENCE_PROJECTION.md; the server never reads evidence files.
"""
import json
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from noesis_harness import project_evidence
from noesis_harness.health_server import HealthServer
from noesis_harness.ui_contract import CONTRACT_VERSION, success


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKLOAD_EVIDENCE_PATH = REPO_ROOT / "docs" / "MULTI_AGENT_WORKLOAD_EVIDENCE.json"
MEMORY_QUALITY_EVIDENCE_PATH = REPO_ROOT / "docs" / "MEMORY_QUALITY_EVIDENCE.json"


class ProjectionHealthServer(HealthServer):
    """HealthServer variant whose caller supplies the evidence projection."""

    def __init__(self, *args, projection=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._projection = projection

    def operator_snapshot(self, *, task_id="", receipt_id="", evidence_projection=None):
        supplied = self._projection if evidence_projection is None else evidence_projection
        return super().operator_snapshot(task_id=task_id, receipt_id=receipt_id, evidence_projection=supplied)


def _projection():
    return project_evidence(WORKLOAD_EVIDENCE_PATH, MEMORY_QUALITY_EVIDENCE_PATH)


def _tampered_workload_path(directory):
    raw = WORKLOAD_EVIDENCE_PATH.read_bytes()
    marker = raw.index(b'"output_digest"')
    hex_start = raw.index(b'sha256:', marker) + len(b'sha256:')
    tampered = raw[:hex_start] + bytes([raw[hex_start] ^ 0x01]) + raw[hex_start + 1:]
    path = Path(directory) / "tampered_workload.json"
    path.write_bytes(tampered)
    return path


def _get(base_url, path):
    request = urllib.request.Request(base_url + path, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        try:
            body = json.loads(error.read().decode("utf-8"))
        finally:
            error.close()
        return error.code, body


def _assert_intact_corpus(case, projection, reference):
    digests = projection["memory_quality_digests"]
    self_digests = reference["memory_quality_digests"]
    case.assertEqual(len(digests), 3)
    case.assertEqual(digests, self_digests)
    case.assertEqual(digests[0]["corpus_schema_version"], "noesis.memory-quality-corpus.v2")
    case.assertTrue(digests[0]["digest_present"])
    case.assertTrue(digests[0]["report_digest"].startswith("sha256:"))
    case.assertEqual(digests[1]["corpus_schema_version"], "noesis.memory-quality-corpus.v3")
    case.assertTrue(digests[1]["digest_present"])
    case.assertTrue(digests[1]["report_digest"].startswith("sha256:"))
    case.assertEqual(digests[2]["corpus_schema_version"], "noesis.memory-quality-evidence.v3")
    case.assertFalse(digests[2]["digest_present"])


class EvidenceProjectionHttpTests(unittest.TestCase):
    def test_http_operator_snapshot_surfaces_verified_projection(self):
        reference = _projection()
        server = ProjectionHealthServer(port=0, projection=reference)
        with server:
            base = "http://%s:%d" % server.address
            code, payload = _get(base, "/api/operator/snapshot")
        self.assertEqual(code, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["contract_version"], CONTRACT_VERSION)
        data = payload["data"]
        self.assertEqual(data["schema_version"], "noesis.operator-snapshot.v1")
        projection = data["evidence_projection"]
        self.assertEqual(projection, reference)
        workload = projection["workload_evidence"]
        self.assertTrue(workload["available"])
        self.assertTrue(workload["digest_verified"])
        self.assertTrue(workload["output_digest"].startswith("sha256:"))
        self.assertEqual(workload["reason"], "")
        _assert_intact_corpus(self, projection, reference)

    def test_http_default_surface_omits_projection(self):
        with HealthServer(port=0) as server:
            base = "http://%s:%d" % server.address
            code, payload = _get(base, "/api/operator/snapshot")
        self.assertEqual(code, 200)
        self.assertNotIn("evidence_projection", payload["data"])

    def test_tampered_workload_fails_closed_over_http_with_200(self):
        with tempfile.TemporaryDirectory() as directory:
            tampered_path = _tampered_workload_path(directory)
            projection = project_evidence(tampered_path, MEMORY_QUALITY_EVIDENCE_PATH)
            self.assertTrue(projection["workload_evidence"]["available"])
            self.assertFalse(projection["workload_evidence"]["digest_verified"])
            server = ProjectionHealthServer(port=0, projection=projection)
            with server:
                base = "http://%s:%d" % server.address
                code, payload = _get(base, "/api/operator/snapshot")
        self.assertEqual(code, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["status"], "ready")
        surfaced = payload["data"]["evidence_projection"]["workload_evidence"]
        self.assertFalse(surfaced["digest_verified"])
        self.assertEqual(surfaced["reason"], "output_digest_mismatch")
        self.assertTrue(surfaced["available"])
        self.assertTrue(surfaced["output_digest"].startswith("sha256:"))
        _assert_intact_corpus(self, payload["data"]["evidence_projection"], projection)


class EvidenceProjectionUiContractTests(unittest.TestCase):
    def test_envelope_accepts_and_preserves_projection_after_redaction(self):
        reference = _projection()
        snapshot = HealthServer().operator_snapshot(evidence_projection=reference)
        envelope = success(snapshot)
        payload = envelope.to_dict()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["contract_version"], CONTRACT_VERSION)
        projection = payload["data"]["evidence_projection"]
        self.assertEqual(projection, reference)
        self.assertNotIn("[REDACTED]", json.dumps(projection))
        wire = json.loads(envelope.to_json())
        self.assertEqual(wire["data"]["evidence_projection"], reference)

    def test_envelope_accepts_tampered_projection_fail_closed_visibility(self):
        with tempfile.TemporaryDirectory() as directory:
            tampered_path = _tampered_workload_path(directory)
            projection = project_evidence(tampered_path, MEMORY_QUALITY_EVIDENCE_PATH)
        snapshot = HealthServer().operator_snapshot(evidence_projection=projection)
        payload = success(snapshot).to_dict()
        surfaced = payload["data"]["evidence_projection"]["workload_evidence"]
        self.assertFalse(surfaced["digest_verified"])
        self.assertEqual(surfaced["reason"], "output_digest_mismatch")
        _assert_intact_corpus(self, payload["data"]["evidence_projection"], projection)


if __name__ == "__main__":
    unittest.main()
