import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.run_operator_evidence_pipeline import run_pipeline
from scripts.release_gate_artifact import build_gate_artifact
from scripts.signed_readiness_receipt import sign_readiness_receipt
from tests.test_external_evidence_readiness import evidence_for, manifest

KEY = "readiness-test-key-2026"
ROOT = Path(__file__).resolve().parents[1]


class VerifyOperatorArtifactCliTests(unittest.TestCase):
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
        snapshot = root / "snapshot.json"
        self.write(snapshot, {"local_execution": {"status": "passed"}, "native_parity": {"status": "not_run"}, "external_comparative": {"status": "not_run"}})
        artifact_root = root / "artifacts"
        report = artifact_root / "operator-report.zip"
        run_pipeline(str(manifest_path), paths, KEY, str(artifact_root), str(snapshot), str(report))
        readiness_snapshot = {"schema_version": "noesis.release-readiness-snapshot.v1", "overall_status": "passed", "snapshot_digest": "cli-snapshot-fixture", "native_host_status": "not_run", "external_lanes_status": "not_run"}
        gate = build_gate_artifact({"status": "passed", "stages": {"post_transfer_audit": {"status": "passed"}, "release_readiness_snapshot": {"status": "passed"}}})
        self.write(artifact_root / "release-readiness.json", readiness_snapshot)
        self.write(artifact_root / "release-gate.json", gate)
        self.write(artifact_root / "signed-readiness-receipt.json", sign_readiness_receipt(readiness_snapshot, gate, 0, "3.14.7", KEY))
        return artifact_root, report

    def run_cli(self, artifact_root, report=None):
        command = [sys.executable, str(ROOT / "scripts/verify_operator_artifact_set.py"), "--root", str(artifact_root), "--key", KEY]
        if report:
            command.extend(["--report", str(report)])
        return subprocess.run(command, cwd=str(ROOT), env={**os.environ, "PYTHONPATH": str(ROOT)}, capture_output=True, text=True)

    def test_python_cli_returns_machine_readable_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact_root, report = self.build_set(Path(directory))
            process = self.run_cli(artifact_root, report)
            self.assertEqual(process.returncode, 0)
            payload = json.loads(process.stdout)
            self.assertEqual(payload["status"], "passed")
            self.assertFalse(payload["automatic_execution"])

    def test_python_cli_returns_blocked_after_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact_root, _ = self.build_set(Path(directory))
            target = artifact_root / "external-evidence-readiness.json"
            target.write_text(target.read_text(encoding="utf-8").replace("noesis.", "tampered."), encoding="utf-8")
            process = self.run_cli(artifact_root)
            self.assertEqual(process.returncode, 2)
            payload = json.loads(process.stdout)
            self.assertEqual(payload["status"], "blocked")

    def test_posix_wrapper_exposes_same_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact_root, _ = self.build_set(Path(directory))
            process = subprocess.run(["sh", str(ROOT / "scripts/verify_operator_artifacts.sh"), "--root", str(artifact_root), "--key", KEY], cwd=str(ROOT), capture_output=True, text=True)
            self.assertEqual(process.returncode, 0)
            self.assertEqual(json.loads(process.stdout)["status"], "passed")


if __name__ == "__main__":
    unittest.main()
