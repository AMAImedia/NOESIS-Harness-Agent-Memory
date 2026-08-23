import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.run_operator_evidence_pipeline import run_pipeline
from scripts.verify_reproducibility_receipt import verify_reproducibility_set
from tests.test_external_evidence_readiness import evidence_for, manifest

KEY = "readiness-test-key-2026"
ROOT = Path(__file__).resolve().parents[1]


class VerifyReproducibilityReceiptTests(unittest.TestCase):
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
        return artifact_root

    def test_independent_verification_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact_root = self.build_set(root)
            result = verify_reproducibility_set(artifact_root, KEY)
            self.assertEqual(result["status"], "passed")
            self.assertFalse(result["automatic_execution"])

    def test_missing_and_tampered_components_block(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact_root = self.build_set(root)
            (artifact_root / "chain-summary.json").unlink()
            self.assertEqual(verify_reproducibility_set(artifact_root, KEY)["reason"], "reproducibility_component_missing")
            artifact_root = self.build_set(root)
            receipt_path = artifact_root / "reproducibility-receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["aggregate_digest"] = "0" * 64
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            self.assertEqual(verify_reproducibility_set(artifact_root, KEY)["reason"], "reproducibility_digest_mismatch")

    def test_wrong_key_and_posix_wrapper(self):
        if os.name == "nt":
            self.skipTest("POSIX shell wrapper is host-gated on Windows")
        with tempfile.TemporaryDirectory() as directory:

            root = Path(directory)
            artifact_root = self.build_set(root)
            self.assertEqual(verify_reproducibility_set(artifact_root, "wrong-reproducibility-key")["reason"], "reproducibility_signature_invalid")
            process = subprocess.run(["sh", str(ROOT / "scripts/verify_reproducibility.sh"), "--root", str(artifact_root), "--key", KEY], cwd=str(ROOT), env={**os.environ, "PYTHONPATH": str(ROOT)}, capture_output=True, text=True)
            self.assertEqual(process.returncode, 0)
            self.assertEqual(json.loads(process.stdout)["status"], "passed")


if __name__ == "__main__":
    unittest.main()
