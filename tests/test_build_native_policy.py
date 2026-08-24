import contextlib
import io
import json
import platform
import sys
import unittest
from unittest.mock import patch

from scripts import build_native


class BuildNativePolicyTests(unittest.TestCase):
    def test_linux_target_mismatch_blocks_run_before_subprocess(self):
        actual_platform = build_native.verify_target("windows")["actual_platform"]
        for target in ("windows", "macos"):
            if target == actual_platform:
                continue
            with self.subTest(target=target), patch("scripts.build_native.subprocess.run") as run:
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = build_native.main(["--backend", "pyinstaller", "--target", target, "--run"])
                self.assertEqual(code, 2)
                run.assert_not_called()
                report = json.loads(output.getvalue())
                self.assertFalse(report["platform_ok"])
                self.assertFalse(report["dry_run"])

    def test_dry_run_is_non_executing_and_reports_command(self):
        with patch("scripts.build_native.subprocess.run") as run:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = build_native.main(["--backend", "briefcase", "--target", "windows"])
            self.assertEqual(code, 2)
            run.assert_not_called()
            report = json.loads(output.getvalue())
            self.assertTrue(report["dry_run"])
            self.assertEqual(report["command"][0], build_native.sys.executable)
            self.assertIn("briefcase", report["command"])

    def test_target_verifier_requires_python_314_and_exact_platform(self):
        report = build_native.verify_target("windows")
        self.assertEqual(report["actual_python"], platform.python_version())
        self.assertIn(report["actual_platform"], {"linux", "windows", "macos"})
        self.assertEqual(report["platform_ok"], report["actual_platform"] == "windows")
        self.assertEqual(report["python_ok"], report["actual_python"].startswith("3.14"))
        with self.subTest(case="wrong_python_version_is_fail_closed"):
            with patch.object(sys, "version_info", (3, 15, 0)):
                wrong = build_native.verify_target("windows")
            self.assertEqual(wrong["actual_python"], "3.15.0")
            self.assertFalse(wrong["python_ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
