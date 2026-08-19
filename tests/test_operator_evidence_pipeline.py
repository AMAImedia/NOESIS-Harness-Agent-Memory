import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_operator_evidence_pipeline import run_pipeline
from scripts.ingest_runner_result import signature
from scripts.post_transfer_audit import audit as post_transfer_audit
from tests.test_external_evidence_readiness import evidence_for, manifest

KEY = "readiness-test-key-2026"


class OperatorEvidencePipelineTests(unittest.TestCase):
    def write_json(self, path, value):
        path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")

    def test_pipeline_writes_matrix_aggregate_and_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = [evidence_for("hermes", "h1"), evidence_for("opencode", "o1"), evidence_for("deepseek_harness", "d1")]
            manifest_path = root / "manifest.json"
            self.write_json(manifest_path, manifest(protocol_fingerprint=evidence[0]["protocol_fingerprint"]))
            evidence_paths = []
            for index, record in enumerate(evidence):
                path = root / ("evidence-%d.json" % index)
                self.write_json(path, record)
                evidence_paths.append(str(path))
            snapshot_path = root / "snapshot.json"
            self.write_json(snapshot_path, {"local_execution": {"status": "passed"}, "native_parity": {"status": "not_run"}, "external_comparative": {"status": "not_run"}})
            report_path = root / "artifacts" / "report.zip"
            result = run_pipeline(str(manifest_path), evidence_paths, KEY, str(root / "artifacts"), str(snapshot_path), str(report_path))
            self.assertEqual(result["status"], "passed")
            self.assertTrue((root / "artifacts/external-evidence-readiness.json").is_file())
            self.assertTrue((root / "artifacts/signed-external-evidence-aggregate.json").is_file())
            self.assertTrue(report_path.is_file())
            verification_path = root / "artifacts/verification-result.json"
            self.assertTrue(verification_path.is_file())
            verification = json.loads(verification_path.read_text(encoding="utf-8"))
            self.assertEqual(verification["verification_status"], "passed")
            self.assertEqual(result["verification_result_digest"], verification["result_digest"])
            self.assertFalse(result["external_execution_claim"])
            self.assertEqual(result["status_vocabulary"], ["passed", "not_run", "blocked", "unsupported"])
            self.assertEqual(result["exit_code"], 0)
            self.assertEqual(result["status_counts"]["passed"], 3)

    def test_pipeline_generates_and_strictly_verifies_readiness_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = [evidence_for("hermes", "h1"), evidence_for("opencode", "o1"), evidence_for("deepseek_harness", "d1")]
            manifest_path = root / "manifest.json"
            self.write_json(manifest_path, manifest(protocol_fingerprint=evidence[0]["protocol_fingerprint"]))
            evidence_paths = []
            for index, record in enumerate(evidence):
                path = root / ("evidence-%d.json" % index)
                self.write_json(path, record)
                evidence_paths.append(str(path))
            artifact_root = root / "artifacts"
            result = run_pipeline(str(manifest_path), evidence_paths, KEY, str(artifact_root), readiness_test_count=636, readiness_python_version="3.14.7")
            self.assertEqual(result["status"], "passed")
            for name in ("release-readiness.json", "release-gate.json", "signed-readiness-receipt.json"):
                self.assertTrue((artifact_root / name).is_file())
            self.assertEqual(post_transfer_audit(artifact_root, KEY)["status"], "passed")
            self.assertFalse(result["external_execution_claim"])

    def test_missing_lane_is_explicit_and_report_is_optional(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = evidence_for("hermes", "h1")
            manifest_path = root / "manifest.json"
            self.write_json(manifest_path, manifest())
            evidence_path = root / "evidence.json"
            self.write_json(evidence_path, record)
            result = run_pipeline(str(manifest_path), [str(evidence_path)], KEY, str(root / "artifacts"))
            self.assertEqual(result["status"], "blocked")
            self.assertIsNone(result["artifacts"]["report_bundle"])
            matrix = json.loads((root / "artifacts/external-evidence-readiness.json").read_text(encoding="utf-8"))
            self.assertEqual(matrix["lanes"]["opencode"]["status"], "blocked")

    def test_all_unsupported_lanes_remain_unsupported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = []
            for system, revision in (("hermes", "h1"), ("opencode", "o1"), ("deepseek_harness", "d1")):
                record = dict(evidence_for(system, revision))
                record["status"] = "unsupported"
                record["signature"] = signature({key: value for key, value in record.items() if key != "signature"}, KEY)
                records.append(record)
            manifest_path = root / "manifest.json"
            self.write_json(manifest_path, manifest(protocol_fingerprint=records[0]["protocol_fingerprint"]))
            paths = []
            for index, record in enumerate(records):
                path = root / ("unsupported-%d.json" % index)
                self.write_json(path, record)
                paths.append(str(path))
            result = run_pipeline(str(manifest_path), paths, KEY, str(root / "artifacts"))
            self.assertEqual(result["status"], "unsupported")
            self.assertEqual(result["exit_code"], 2)
            self.assertEqual(result["status_counts"]["unsupported"], 3)

    def test_report_output_requires_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            self.write_json(manifest_path, {"revisions": {}})
            with self.assertRaisesRegex(ValueError, "report_output_requires_snapshot"):
                run_pipeline(str(manifest_path), [], KEY, str(root / "artifacts"), report_output=str(root / "report.zip"))


if __name__ == "__main__":
    unittest.main()
