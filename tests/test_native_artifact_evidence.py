from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.verify_native_artifact import artifact_digest, verify


class NativeArtifactEvidenceTests(unittest.TestCase):
    def test_linux_host_never_claims_windows_native_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "noesis-harness.exe"
            artifact.write_bytes(b"not-a-real-native-build")
            report = verify("windows", str(artifact))
            self.assertEqual(report["evidence_status"], "not_run")
            self.assertEqual(report["reason"], "target_host_or_python_mismatch")
            self.assertFalse(report["host"]["platform_ok"])

    def test_macos_requires_app_bundle_shape(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "NOESIS-Harness-Agent-Memory.zip"
            artifact.write_bytes(b"wrong shape")
            report = verify("macos", str(artifact), development_unsigned=True)
            self.assertEqual(report["evidence_status"], "not_run")
            self.assertEqual(report["artifact_shape_reason"], "macos_app_bundle_required")

    def test_digest_is_stable_for_bundle_file_order(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / "NOESIS.app"
            (bundle / "Contents" / "MacOS").mkdir(parents=True)
            (bundle / "Contents" / "MacOS" / "main").write_bytes(b"main")
            (bundle / "Contents" / "Info.plist").write_bytes(b"plist")
            first, count = artifact_digest(bundle)
            second, second_count = artifact_digest(bundle)
            self.assertEqual(first, second)
            self.assertEqual((count, second_count), (2, 2))

    def test_development_unsigned_is_explicit_not_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "NOESIS.app"
            artifact.mkdir()
            (artifact / "Contents").mkdir()
            report = verify("macos", str(artifact), development_unsigned=True)
            if report["host"]["platform_ok"] and report["host"]["python_ok"]:
                self.assertIn(report["evidence_status"], {"development_unsigned", "signed_dev"})
            else:
                self.assertEqual(report["evidence_status"], "not_run")


if __name__ == "__main__":
    unittest.main()
