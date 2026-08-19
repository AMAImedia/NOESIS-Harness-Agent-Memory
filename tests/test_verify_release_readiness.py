import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.release_readiness_snapshot import build_snapshot
from scripts.verify_release_readiness import verify_file

ROOT = Path(__file__).resolve().parents[1]


class VerifyReleaseReadinessTests(unittest.TestCase):
    def write(self, path, value):
        path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")

    def test_valid_and_tampered_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "release-readiness.json"
            snapshot = build_snapshot({"status": "passed"}, 622, "3.14.7")
            self.write(path, snapshot)
            self.assertEqual(verify_file(path)["status"], "passed")
            snapshot["validated_test_count"] = 623
            self.write(path, snapshot)
            self.assertEqual(verify_file(path)["reason"], "readiness_snapshot_digest_mismatch")

    def test_missing_snapshot_and_wrapper(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.json"
            self.assertEqual(verify_file(missing)["reason"], "readiness_snapshot_missing")
            path = Path(directory) / "release-readiness.json"
            self.write(path, build_snapshot({"status": "passed"}, 622, "3.14.7"))
            process = subprocess.run(["sh", str(ROOT / "scripts/verify_release_readiness.sh"), "--snapshot", str(path)], cwd=str(ROOT), env={**os.environ, "PYTHONPATH": str(ROOT)}, capture_output=True, text=True)
            self.assertEqual(process.returncode, 0)
            self.assertEqual(json.loads(process.stdout)["status"], "passed")


if __name__ == "__main__":
    unittest.main()
