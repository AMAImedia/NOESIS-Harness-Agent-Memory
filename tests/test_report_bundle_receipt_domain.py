import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from noesis_harness.report_bundle import build_report_bundle, verify_report_bundle


class ReportBundleReceiptDomainTests(unittest.TestCase):
    key = b"report-receipt-domain-key"

    def test_v2_receipt_domain_round_trip_is_deterministic_and_audit_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = {"status": "passed", "receipt_count": 3, "claim": True, "execution_claim": True, "comparative_claim": True}
            first = build_report_bundle(root / "one.zip", local_execution={"status": "passed"}, native_parity={"status": "not_run"}, external_comparative={"status": "not_run"}, lifecycle_receipt_audit=audit, signing_key=self.key)
            second = build_report_bundle(root / "two.zip", local_execution={"status": "passed"}, native_parity={"status": "not_run"}, external_comparative={"status": "not_run"}, lifecycle_receipt_audit=audit, signing_key=self.key)
            self.assertEqual((root / "one.zip").read_bytes(), (root / "two.zip").read_bytes())
            self.assertEqual(verify_report_bundle(root / "one.zip", self.key)["status"], "passed")
            self.assertIn("lifecycle_receipt_audit", first["domains"])

    def test_v1_bundle_remains_verifiable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.zip"
            build_report_bundle(path, local_execution={"status": "passed"}, native_parity={"status": "not_run"}, external_comparative={"status": "not_run"}, signing_key=self.key)
            result = verify_report_bundle(path, self.key)
            self.assertEqual(result["status"], "passed")
            self.assertNotIn("lifecycle_receipt_audit", result["domains"])

    def test_receipt_domain_archive_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "bundle.zip"
            build_report_bundle(path, local_execution={}, native_parity={}, external_comparative={}, lifecycle_receipt_audit={"status": "passed"}, signing_key=self.key)
            tampered = root / "tampered.zip"
            with zipfile.ZipFile(path) as source, zipfile.ZipFile(tampered, "w", compression=zipfile.ZIP_STORED) as target:
                for name in source.namelist():
                    data = source.read(name)
                    if name == "lifecycle_receipt_audit.json":
                        value = json.loads(data.decode())
                        value["claim"] = True
                        data = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
                    target.writestr(name, data)
            result = verify_report_bundle(tampered, self.key)
            self.assertEqual(result["status"], "blocked")
            self.assertIn(result["reason"], {"domain_digest_mismatch:lifecycle_receipt_audit", "bundle_signature_invalid"})


if __name__ == "__main__":
    unittest.main()
