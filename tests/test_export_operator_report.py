import tempfile
import unittest
from pathlib import Path

from scripts.export_operator_report import export_snapshot
from noesis_harness.report_bundle import verify_report_bundle


class ExportOperatorReportTests(unittest.TestCase):
    key = b"operator-snapshot-export-key"

    def test_snapshot_mapping_and_redaction(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.zip"
            snapshot = {"readiness": "ready", "local_execution": {"status": "passed", "execution_claim": True, "operator_token": "secret"}, "telemetry": {"native_parity": {"status": "not_run", "execution_claim": False}}, "external_comparative": {"status": "not_run", "comparative_claim": False, "external_execution_claim": False}}
            result = export_snapshot(snapshot, str(output), self.key)
            self.assertEqual(verify_report_bundle(output, self.key)["status"], "passed")
            self.assertEqual(result["domains"], ["local_execution", "native_parity", "external_comparative"])

    def test_missing_domains_remain_not_run(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.zip"
            export_snapshot({}, str(output), self.key)
            verified = verify_report_bundle(output, self.key)
            self.assertEqual(verified["status"], "passed")
            import zipfile, json
            with zipfile.ZipFile(output) as archive:
                native = json.loads(archive.read("native_parity.json"))
                external = json.loads(archive.read("external_comparative.json"))
            self.assertEqual(native["status"], "not_run")
            self.assertEqual(external["status"], "not_run")
            self.assertFalse(external["comparative_claim"])


if __name__ == "__main__":
    unittest.main()
