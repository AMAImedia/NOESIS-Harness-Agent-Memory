import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_operator_evidence_pipeline import run_pipeline
from scripts.signed_verification_result import verify_signed_verification_result
from scripts.verify_operator_artifact_set import main
from tests.test_external_evidence_readiness import evidence_for, manifest

KEY = "readiness-test-key-2026"


class SignedVerificationResultTests(unittest.TestCase):
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

    def test_cli_writes_and_signs_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact_root = self.build_set(root)
            output = root / "verification-result.json"
            self.assertEqual(main(["--root", str(artifact_root), "--key", KEY, "--signed-output", str(output)]), 0)
            signed = json.loads(output.read_text(encoding="utf-8"))
            checked = verify_signed_verification_result(signed, KEY)
            self.assertEqual(checked["status"], "passed")
            self.assertEqual(checked["verification_status"], "passed")
            self.assertFalse(signed["external_execution_claim"])

    def test_tamper_and_wrong_key_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact_root = self.build_set(root)
            output = root / "verification-result.json"
            self.assertEqual(main(["--root", str(artifact_root), "--key", KEY, "--signed-output", str(output)]), 0)
            signed = json.loads(output.read_text(encoding="utf-8"))
            signed["verification_status"] = "blocked"
            self.assertEqual(verify_signed_verification_result(signed, KEY)["reason"], "verification_result_digest_mismatch")
            original = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(verify_signed_verification_result(original, "different-verification-key")["reason"], "verification_result_signature_invalid")


if __name__ == "__main__":
    unittest.main()
