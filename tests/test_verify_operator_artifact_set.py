import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_operator_evidence_pipeline import run_pipeline
from scripts.verify_operator_artifact_set import verify_artifact_set
from tests.test_external_evidence_readiness import evidence_for, manifest

KEY = "readiness-test-key-2026"


class VerifyOperatorArtifactSetTests(unittest.TestCase):
    def write(self, path, value):
        path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")

    def build_set(self, root, with_report=True):
        evidence = [evidence_for("hermes", "h1"), evidence_for("opencode", "o1"), evidence_for("deepseek_harness", "d1")]
        manifest_path = root / "manifest.json"
        self.write(manifest_path, manifest(protocol_fingerprint=evidence[0]["protocol_fingerprint"]))
        paths = []
        for index, record in enumerate(evidence):
            path = root / ("evidence-%d.json" % index)
            self.write(path, record)
            paths.append(str(path))
        snapshot = root / "snapshot.json"
        self.write(snapshot, {"local_execution": {"status": "passed"}, "native_parity": {"status": "not_run"}, "external_comparative": {"status": "not_run"}})
        report = root / "artifacts" / "report.zip" if with_report else None
        run_pipeline(str(manifest_path), paths, KEY, str(root / "artifacts"), str(snapshot), str(report) if report else None)
        return root / "artifacts", report

    def test_valid_transferred_set_and_report_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact_root, report = self.build_set(Path(directory))
            result = verify_artifact_set(artifact_root, KEY, str(report))
            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["checks"]["inventory"]["status"], "passed")
            self.assertEqual(result["checks"]["report_bundle"]["status"], "passed")
            self.assertFalse(result["automatic_execution"])

    def test_tampering_inventory_listed_file_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact_root, _ = self.build_set(Path(directory), with_report=False)
            target = artifact_root / "signed-external-evidence-aggregate.json"
            target.write_text(target.read_text(encoding="utf-8").replace("signed-external", "tampered-external"), encoding="utf-8")
            result = verify_artifact_set(artifact_root, KEY)
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["checks"]["inventory"]["reason"], "inventory_file_mismatch")

    def test_missing_manifest_and_outside_report_are_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = verify_artifact_set(root, KEY)
            self.assertEqual(result["reason"], "artifact_manifest_missing")
            artifact_root, _ = self.build_set(root, with_report=False)
            outside = root / "outside.zip"
            outside.write_bytes(b"not-a-bundle")
            result = verify_artifact_set(artifact_root, KEY, str(outside))
            self.assertEqual(result["reason"], "report_path_invalid")


if __name__ == "__main__":
    unittest.main()
