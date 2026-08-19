import tempfile
import unittest
from pathlib import Path

from scripts.export_operator_report import export_snapshot
from noesis_harness.report_bundle import verify_report_bundle


class ExportOperatorReceiptDomainTests(unittest.TestCase):
    key = b"operator-receipt-export-key"

    def test_receipt_audit_selects_v2_and_remains_claim_conservative(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.zip"
            audit = {"status": "passed", "record_id": "r", "receipt_count": 3, "claim": True, "execution_claim": True, "comparative_claim": True}
            result = export_snapshot({}, str(output), self.key, audit)
            self.assertIn("lifecycle_receipt_audit", result["domains"])
            verified = verify_report_bundle(output, self.key)
            self.assertEqual(verified["status"], "passed")
            self.assertFalse(verified["claim"])

    def test_no_receipt_audit_keeps_v1_default(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.zip"
            result = export_snapshot({}, str(output), self.key)
            self.assertNotIn("lifecycle_receipt_audit", result["domains"])


if __name__ == "__main__":
    unittest.main()
