import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.post_transfer_audit import audit
from scripts.signed_readiness_receipt import sign_readiness_receipt
from scripts.release_gate_artifact import build_gate_artifact
from scripts.run_operator_evidence_pipeline import run_pipeline
from tests.test_external_evidence_readiness import evidence_for, manifest

KEY = "readiness-test-key-2026"
ROOT = Path(__file__).resolve().parents[1]


class PostTransferAuditTests(unittest.TestCase):
    def write(self, path, value):
        path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")

    def build_set(self, root):
        evidence = [evidence_for("hermes", "h1"), evidence_for("opencode", "o1"), evidence_for("deepseek_harness", "d1")]
        manifest_path = root / "manifest.json"
        self.write(manifest_path, manifest(protocol_fingerprint=evidence[0]["protocol_fingerprint"]))
        paths = []
        for index, record in enumerate(evidence):
            path = root / ("evidence-%d.json" % index)
            self.write(path, record)
            paths.append(str(path))
        artifact_root = root / "artifacts"
        run_pipeline(str(manifest_path), paths, KEY, str(artifact_root))
        snapshot = {"schema_version": "noesis.release-readiness-snapshot.v1", "overall_status": "passed", "snapshot_digest": "snapshot-fixture-digest", "native_host_status": "not_run", "external_lanes_status": "not_run"}
        gate = build_gate_artifact({"status": "passed", "stages": {"post_transfer_audit": {"status": "passed"}, "release_readiness_snapshot": {"status": "passed"}}})
        self.write(artifact_root / "release-readiness.json", snapshot)
        self.write(artifact_root / "release-gate.json", gate)
        receipt = sign_readiness_receipt(snapshot, gate, 0, "3.14.7", KEY)
        self.write(artifact_root / "signed-readiness-receipt.json", receipt)
        return artifact_root

    def test_full_post_transfer_audit_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact_root = self.build_set(Path(directory))
            result = audit(artifact_root, KEY)
            self.assertEqual(result["status"], "passed")
            self.assertEqual(set(result["stages"]), {"composition", "artifact_chain", "reproducibility", "release_gate_artifact"})
            self.assertFalse(result["automatic_execution"])

    def test_failed_stage_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact_root = self.build_set(Path(directory))
            (artifact_root / "reproducibility-receipt.json").unlink()
            result = audit(artifact_root, KEY)
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["failed_stage"], "composition")

    def test_posix_wrapper_outputs_one_json_object(self):
        if os.name == "nt":
            self.skipTest("POSIX shell wrapper is host-gated on Windows")
        with tempfile.TemporaryDirectory() as directory:

            artifact_root = self.build_set(Path(directory))
            process = subprocess.run(["sh", str(ROOT / "scripts/post_transfer_audit.sh"), "--root", str(artifact_root), "--key", KEY], cwd=str(ROOT), env={**os.environ, "PYTHONPATH": str(ROOT)}, capture_output=True, text=True)
            self.assertEqual(process.returncode, 0)
            self.assertEqual(json.loads(process.stdout)["status"], "passed")


if __name__ == "__main__":
    unittest.main()
