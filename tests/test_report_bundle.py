import tempfile
import unittest
import zipfile
from pathlib import Path

from noesis_harness.report_bundle import build_report_bundle, verify_report_bundle


class ReportBundleTests(unittest.TestCase):
    key = b"report-bundle-signing-key-1234"

    def domains(self):
        return {"local_execution": {"status": "passed", "execution_claim": True}, "native_parity": {"status": "not_run", "execution_claim": False}, "external_comparative": {"status": "not_run", "comparative_claim": False}}

    def test_deterministic_signed_round_trip_is_export_only(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.zip"
            second = Path(directory) / "second.zip"
            args = self.domains()
            one = build_report_bundle(first, **args, signing_key=self.key)
            two = build_report_bundle(second, **args, signing_key=self.key)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(one["bundle_digest"], two["bundle_digest"])
            verified = verify_report_bundle(first, self.key)
            self.assertEqual(verified["status"], "passed")
            self.assertFalse(verified["claim"])

    def test_domain_drift_and_signature_tamper_are_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.zip"
            build_report_bundle(path, **self.domains(), signing_key=self.key)
            with zipfile.ZipFile(path, "r") as source:
                entries = {name: source.read(name) for name in source.namelist()}
            entries["native_parity.json"] = b'{"status":"passed","execution_claim":true}\n'
            with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as target:
                for name, content in entries.items():
                    target.writestr(name, content)
            self.assertEqual(verify_report_bundle(path, self.key)["reason"], "domain_digest_mismatch:native_parity")

    def test_missing_domain_and_wrong_key_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.zip"
            build_report_bundle(path, **self.domains(), signing_key=self.key)
            with zipfile.ZipFile(path, "r") as source:
                entries = {name: source.read(name) for name in source.namelist() if name != "external_comparative.json"}
            with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as target:
                for name, content in entries.items():
                    target.writestr(name, content)
            self.assertEqual(verify_report_bundle(path, self.key)["reason"], "bundle_file_set_mismatch")
            build_report_bundle(path, **self.domains(), signing_key=self.key)
            self.assertEqual(verify_report_bundle(path, b"wrong-key-123456")["reason"], "bundle_signature_invalid")


if __name__ == "__main__":
    unittest.main()
