import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.release_gate_artifact import build_gate_artifact
from scripts.verify_release_gate_artifact import verify_file

ROOT = Path(__file__).resolve().parents[1]


class ReleaseGateArtifactTests(unittest.TestCase):
    result = {"status": "passed", "stages": {"post_transfer_audit": {"status": "passed"}, "release_readiness_snapshot": {"status": "passed"}}}

    def test_deterministic_and_tamper_rejection(self):
        first = build_gate_artifact(self.result)
        second = build_gate_artifact(dict(self.result))
        self.assertEqual(first, second)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "release-gate.json"
            path.write_text(json.dumps(first), encoding="utf-8")
            self.assertEqual(verify_file(path)["status"], "passed")
            first["status"] = "blocked"
            path.write_text(json.dumps(first), encoding="utf-8")
            self.assertEqual(verify_file(path)["reason"], "release_gate_artifact_digest_mismatch")

    def test_missing_and_wrapper(self):
        if os.name == "nt":
            self.skipTest("POSIX shell wrapper is host-gated on Windows")
        with tempfile.TemporaryDirectory() as directory:

            root = Path(directory)
            missing = root / "missing.json"
            self.assertEqual(verify_file(missing)["reason"], "release_gate_artifact_missing")
            path = root / "release-gate.json"
            path.write_text(json.dumps(build_gate_artifact(self.result)), encoding="utf-8")
            process = subprocess.run(["sh", str(ROOT / "scripts/verify_release_gate_artifact.sh"), "--artifact", str(path)], cwd=str(ROOT), env={**os.environ, "PYTHONPATH": str(ROOT)}, capture_output=True, text=True)
            self.assertEqual(process.returncode, 0)
            self.assertEqual(json.loads(process.stdout)["status"], "passed")


if __name__ == "__main__":
    unittest.main()
