import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.release_gate import run_gate
from scripts.release_readiness_snapshot import build_snapshot
from scripts.release_gate_artifact import build_gate_artifact
from scripts.signed_readiness_receipt import sign_readiness_receipt
from scripts.run_operator_evidence_pipeline import run_pipeline
from tests.test_external_evidence_readiness import evidence_for, manifest

KEY = "readiness-test-key-2026"
ROOT = Path(__file__).resolve().parents[1]


class ReleaseGateTests(unittest.TestCase):
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
        snapshot_path = root / "release-readiness.json"
        snapshot = build_snapshot({"status": "passed"}, 624, "3.14.7")
        self.write(snapshot_path, snapshot)
        gate = build_gate_artifact({"status": "passed", "stages": {"post_transfer_audit": {"status": "passed"}, "release_readiness_snapshot": {"status": "passed"}}})
        self.write(artifact_root / "release-readiness.json", snapshot)
        self.write(artifact_root / "release-gate.json", gate)
        self.write(artifact_root / "signed-readiness-receipt.json", sign_readiness_receipt(snapshot, gate, 624, "3.14.7", KEY))
        return artifact_root, snapshot_path

    def test_gate_passes_with_separate_stage_results(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact_root, snapshot = self.build_set(Path(directory))
            result = run_gate(artifact_root, KEY, snapshot)
            self.assertEqual(result["status"], "passed")
            self.assertEqual(set(result["stages"]), {"post_transfer_audit", "release_readiness_snapshot", "release_gate_artifact"})

    def test_gate_preserves_failed_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact_root, snapshot = self.build_set(Path(directory))
            (artifact_root / "chain-summary.json").unlink()
            result = run_gate(artifact_root, KEY, snapshot)
            self.assertEqual(result["failed_stage"], "post_transfer_audit")
            self.write(snapshot, {"schema_version": "bad"})
            artifact_root, snapshot = self.build_set(Path(directory))
            self.write(snapshot, {"schema_version": "bad"})
            result = run_gate(artifact_root, KEY, snapshot)
            self.assertEqual(result["failed_stage"], "release_readiness_snapshot")

    def test_gate_stage_status_mismatch_is_blocked_independently(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact_root, snapshot = self.build_set(root)
            mismatch_path = root / "mismatch-gate.json"
            mismatch = build_gate_artifact({"status": "passed", "stages": {"post_transfer_audit": {"status": "blocked"}, "release_readiness_snapshot": {"status": "passed"}}})
            self.write(mismatch_path, mismatch)
            result = run_gate(artifact_root, KEY, snapshot, mismatch_path)
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["failed_stage"], "release_gate_artifact")
            self.assertEqual(result["stages"]["release_gate_artifact"]["reason"], "release_gate_stage_status_mismatch")

    def test_existing_gate_artifact_consistency(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact_root, snapshot = self.build_set(Path(directory))
            first = run_gate(artifact_root, KEY, snapshot)
            gate_path = artifact_root / "release-gate.json"
            gate_path.write_text(json.dumps({"schema_version": "noesis.release-gate-artifact.v1", "status": first["status"], "failed_stage": first.get("failed_stage"), "stages": first["stages"], "automatic_execution": False, "external_execution_claim": False, "claim_boundary": "release_gate_integrity_summary_only", "artifact_digest": "invalid"}), encoding="utf-8")
            blocked = run_gate(artifact_root, KEY, snapshot, gate_path)
            self.assertEqual(blocked["failed_stage"], "post_transfer_audit")

    def test_posix_wrapper_returns_json(self):
        if os.name == "nt":
            self.skipTest("POSIX shell wrapper is host-gated on Windows")
        with tempfile.TemporaryDirectory() as directory:

            artifact_root, snapshot = self.build_set(Path(directory))
            process = subprocess.run(["sh", str(ROOT / "scripts/release_gate.sh"), "--root", str(artifact_root), "--key", KEY, "--snapshot", str(snapshot)], cwd=str(ROOT), env={**os.environ, "PYTHONPATH": str(ROOT)}, capture_output=True, text=True)
            self.assertEqual(process.returncode, 0)
            self.assertEqual(json.loads(process.stdout)["status"], "passed")


if __name__ == "__main__":
    unittest.main()
