import contextlib
import io
import unittest
from unittest.mock import patch

from scripts import build_native


class BuildNativePolicyTests(unittest.TestCase):
    def test_linux_target_mismatch_blocks_run_before_subprocess(self):
        for target in ("windows", "macos"):
            with self.subTest(target=target), patch("scripts.build_native.subprocess.run") as run:
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = build_native.main(["--backend", "pyinstaller", "--target", target, "--run"])
                self.assertEqual(code, 2)
                run.assert_not_called()
                report = __import__("json").loads(output.getvalue())
                self.assertFalse(report["python_ok"] is False and report["platform_ok"] is True)
                self.assertFalse(report["platform_ok"])
                self.assertFalse(report["dry_run"])

    def test_dry_run_is_non_executing_and_reports_command(self):
        with patch("scripts.build_native.subprocess.run") as run:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = build_native.main(["--backend", "briefcase", "--target", "windows"])
            self.assertEqual(code, 2)
            run.assert_not_called()
            report = __import__("json").loads(output.getvalue())
            self.assertTrue(report["dry_run"])
            self.assertEqual(report["command"][0], build_native.sys.executable)
            self.assertIn("briefcase", report["command"])

    def test_target_verifier_requires_python_314_and_exact_platform(self):
        report = build_native.verify_target("windows")
        self.assertEqual(report["actual_python"], "3.14.7")
        self.assertIn(report["actual_platform"], {"linux", "windows", "macos"})
        self.assertEqual(report["platform_ok"], report["actual_platform"] == "windows")
        self.assertEqual(report["python_ok"], True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
