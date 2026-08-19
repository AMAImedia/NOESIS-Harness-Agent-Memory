import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ReportBundleCliTests(unittest.TestCase):
    def test_create_verify_and_wrong_key(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, value in (("local", {"status": "passed"}), ("native", {"status": "not_run"}), ("external", {"status": "not_run"})):
                (root / (name + ".json")).write_text(json.dumps(value), encoding="utf-8")
            bundle = root / "report.zip"
            env = dict(os.environ, PYTHONPATH=str(Path(__file__).parents[1]), NOESIS_REPORT_SIGNING_KEY="cli-test-signing-key")
            command = [sys.executable, "scripts/report_bundle.py"]
            created = subprocess.run(command + ["create", "--local", str(root / "local.json"), "--native", str(root / "native.json"), "--external", str(root / "external.json"), "--output", str(bundle)], cwd=env["PYTHONPATH"], env=env, capture_output=True, text=True)
            self.assertEqual(created.returncode, 0, created.stderr)
            verified = subprocess.run(command + ["verify", "--bundle", str(bundle)], cwd=env["PYTHONPATH"], env=env, capture_output=True, text=True)
            self.assertEqual(verified.returncode, 0, verified.stderr)
            wrong = subprocess.run(command + ["verify", "--bundle", str(bundle)], cwd=env["PYTHONPATH"], env=dict(env, NOESIS_REPORT_SIGNING_KEY="wrong-key-123456"), capture_output=True, text=True)
            self.assertEqual(wrong.returncode, 2)
            self.assertEqual(json.loads(wrong.stdout)["status"], "blocked")

    def test_missing_key_is_blocked(self):
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).parents[1]) , NOESIS_REPORT_SIGNING_KEY="")
        result = subprocess.run([sys.executable, "scripts/report_bundle.py", "verify", "--bundle", "/missing/report.zip"], cwd=env["PYTHONPATH"], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
