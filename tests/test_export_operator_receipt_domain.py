import tempfile
import unittest
from pathlib import Path

from scripts.export_operator_report import export_snapshot
from noesis_harness.report_bundle import verify_report_bundle
from scripts.aggregate_external_evidence import aggregate_external_evidence
from tests.test_external_evidence_readiness import evidence_for, manifest


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

    def test_signed_external_aggregate_is_embedded_without_claim_escalation(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.zip"
            evidence = [evidence_for("hermes", "h1"), evidence_for("opencode", "o1"), evidence_for("deepseek_harness", "d1")]
            aggregate = aggregate_external_evidence(manifest(protocol_fingerprint=evidence[0]["protocol_fingerprint"]), evidence, self.key.decode())
            result = export_snapshot({}, str(output), self.key, external_aggregate=aggregate)
            self.assertIn("external_comparative", result["domains"])
            verified = verify_report_bundle(output, self.key)
            self.assertEqual(verified["status"], "passed")
            self.assertFalse(verified["claim"])

    def test_tampered_external_aggregate_blocks_export(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.zip"
            evidence = [evidence_for("hermes", "h1"), evidence_for("opencode", "o1"), evidence_for("deepseek_harness", "d1")]
            aggregate = aggregate_external_evidence(manifest(protocol_fingerprint=evidence[0]["protocol_fingerprint"]), evidence, self.key.decode())
            aggregate["matrix_digest"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "external_aggregate_verification:aggregate_digest_mismatch"):
                export_snapshot({}, str(output), self.key, external_aggregate=aggregate)
            self.assertFalse(output.exists())

    def test_no_receipt_audit_keeps_v1_default(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.zip"
            result = export_snapshot({}, str(output), self.key)
            self.assertNotIn("lifecycle_receipt_audit", result["domains"])


if __name__ == "__main__":
    unittest.main()
