from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.verify_native_artifact import (
    artifact_digest,
    locate_signtool,
    signature_evidence,
    verify,
)


class NativeArtifactEvidenceTests(unittest.TestCase):
    def test_linux_host_never_claims_windows_native_evidence(self):
        if os.name != "posix":
            self.skipTest("Linux host evidence case is not applicable on Windows")
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


def _ok_windows_host() -> dict:
    return {
        "target": "windows",
        "actual_platform": "windows",
        "actual_python": "3.14.7",
        "architecture": "AMD64",
        "python_ok": True,
        "platform_ok": True,
    }


class SigntoolProbeTests(unittest.TestCase):
    def test_missing_when_path_empty_and_no_kits_roots(self):
        with mock.patch("scripts.verify_native_artifact.shutil.which", return_value=None):
            result = locate_signtool(search_roots=[])
        self.assertEqual(result, {"status": "missing"})

    def test_found_picks_highest_kits_version_with_stubbed_subprocess(self):
        with tempfile.TemporaryDirectory() as directory:
            kits_bin = Path(directory) / "Windows Kits" / "10" / "bin"
            for version in ("10.0.19041.0", "10.0.26100.0", "archive"):
                tool = kits_bin / version / "x64" / "signtool.exe"
                tool.parent.mkdir(parents=True)
                tool.write_bytes(b"MZ fake signtool")

            calls = []

            def fake_run(command, **kwargs):
                calls.append((command, kwargs))
                return subprocess.CompletedProcess(command, 0, stdout="SignTool 10.0.26100.0\n", stderr="")

            with mock.patch("scripts.verify_native_artifact.shutil.which", return_value=None):
                with mock.patch("scripts.verify_native_artifact.subprocess.run", side_effect=fake_run):
                    result = locate_signtool(search_roots=[str(kits_bin)])

            self.assertEqual(result["status"], "found")
            self.assertEqual(result["source"], "windows_kits")
            self.assertTrue(result["path"].endswith("10.0.26100.0\\x64\\signtool.exe"))
            self.assertEqual(result["version"], "SignTool 10.0.26100.0")
            self.assertEqual(len(calls), 1)
            command, kwargs = calls[0]
            self.assertEqual(command[1:], ["--version"])
            self.assertEqual(kwargs.get("timeout"), 20)

    def test_probe_never_escalates_exceptions(self):
        with mock.patch("scripts.verify_native_artifact.shutil.which", side_effect=OSError("boom")):
            result = locate_signtool(search_roots=[])
        self.assertEqual(result["status"], "missing")

    def test_signature_section_missing_keeps_legacy_wording(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "noesis-harness.exe"
            artifact.write_bytes(b"not-signed")

            def refuse(*args, **kwargs):
                raise AssertionError("no signing subprocess may run")

            with mock.patch("scripts.verify_native_artifact.locate_signtool", return_value={"status": "missing"}):
                with mock.patch("scripts.verify_native_artifact.subprocess.run", side_effect=refuse):
                    section = signature_evidence(artifact, "windows")

        self.assertEqual(section["status"], "not_run")
        self.assertEqual(section["tool"], "signtool")
        self.assertEqual(section["reason"], "signtool_unavailable")

    def test_signature_section_present_records_probe_but_stays_not_run(self):
        probe = {"status": "found", "source": "windows_kits", "path": "C:\\fake\\signtool.exe", "version": "SignTool 10.0"}

        def refuse(*args, **kwargs):
            raise AssertionError("no cert operation is requested by this script")

        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "noesis-harness.exe"
            artifact.write_bytes(b"not-signed")
            with mock.patch("scripts.verify_native_artifact.locate_signtool", return_value=probe):
                with mock.patch("scripts.verify_native_artifact.subprocess.run", side_effect=refuse):
                    section = signature_evidence(artifact, "windows")

        self.assertEqual(section["status"], "not_run")
        self.assertEqual(section["reason"], "signtool_present_cert_unavailable")
        self.assertEqual(section["tool_path"], "C:\\fake\\signtool.exe")
        self.assertEqual(section["tool_version"], "SignTool 10.0")

    def test_full_evidence_is_deterministic_apart_from_generated_at(self):
        probe = {"status": "found", "source": "path", "path": "C:\\fake\\signtool.exe", "version": "SignTool 10.0"}
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "noesis-harness.exe"
            artifact.write_bytes(b"deterministic-bytes")
            with mock.patch("scripts.verify_native_artifact.verify_host", return_value=_ok_windows_host()):
                with mock.patch("scripts.verify_native_artifact.locate_signtool", return_value=probe):
                    first = verify("windows", str(artifact), development_unsigned=True)
                    second = verify("windows", str(artifact), development_unsigned=True)
        del first["generated_at"], second["generated_at"]
        self.assertEqual(first, second)
        self.assertEqual(second["evidence_status"], "development_unsigned")
        self.assertEqual(second["signature"]["reason"], "signtool_present_cert_unavailable")

    def test_real_dist_exe_regenerates_evidence_when_host_gate_passes(self):
        artifact = Path(__file__).resolve().parents[1] / "dist" / "noesis-harness.exe"
        if not artifact.is_file():
            self.skipTest("dist/noesis-harness.exe not built on this host")
        report = verify("windows", str(artifact), development_unsigned=True)
        if not report["host"]["platform_ok"] or not report["host"]["python_ok"]:
            self.skipTest("target host or python gate not satisfiable here")
        self.assertEqual(report["evidence_status"], "development_unsigned")
        self.assertEqual(report["signature"]["status"], "not_run")
        self.assertIn(report["signature"]["reason"], {"signtool_present_cert_unavailable", "signtool_unavailable"})
        if report["signature"]["reason"] == "signtool_present_cert_unavailable":
            self.assertTrue(report["signature"].get("tool_path"))
            # signtool rejects "--version"; an honest probe may report null here.
            self.assertIn(type(report["signature"].get("tool_version")), (str, type(None)))


if __name__ == "__main__":
    unittest.main()
