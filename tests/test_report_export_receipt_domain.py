import hashlib
import hmac
import json
import tempfile
import unittest
import urllib.request
from pathlib import Path
from types import SimpleNamespace

from noesis_harness.health_server import HealthServer
from noesis_harness.report_bundle import verify_report_bundle
from noesis_harness.report_export_action import ReportExportAction, ReportExportActionError, ReportExportActionExecutor, _digest, _canonical


class ReportExportReceiptDomainActionTests(unittest.TestCase):
    key = b"report-export-receipt-domain-key"

    def snapshot(self):
        return {"local_execution": {"status": "passed"}, "native_parity": {"status": "not_run"}, "external_comparative": {"status": "not_run"}}

    def receipt_file(self, path):
        common = {"record_id": "record-1", "bundle_digest": "b" * 64, "audit_digest": "a" * 64}
        receipts = []
        for index, (action, state) in enumerate((("preflight", "awaiting_approval"), ("approve", "approved"), ("import", "imported"))):
            unsigned = {"schema_version": "noesis.lifecycle-audit-ingestion-receipt.v1", "action_id": "ingest-%d" % index, "action": action, "operator_id": "operator-1", "record_id": common["record_id"], "state": state, "bundle_digest": common["bundle_digest"], "audit_digest": common["audit_digest"], "execution_allowed": False, "automatic_import": False, "claim": False, "created_at": index + 1}
            receipts.append({**unsigned, "signature": hmac.new(self.key, _canonical(unsigned), hashlib.sha256).hexdigest()})
        path.write_text(json.dumps({**common, "receipts": receipts}, sort_keys=True), encoding="utf-8")

    def test_authenticated_export_includes_verified_receipt_domain(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt_path = root / "receipt-audit.json"
            self.receipt_file(receipt_path)
            snapshot = self.snapshot()
            executor = ReportExportActionExecutor(root / "reports", root / "audit.jsonl", signing_key=self.key, snapshot_provider=lambda: snapshot)
            action = ReportExportAction.sign(action_id="v2-export", operator_id="operator-1", session_id="session-1", output_name="report.zip", snapshot_digest=_digest(snapshot), signing_key=self.key, receipt_audit_path=str(receipt_path))
            result = executor.handle(action, SimpleNamespace(authenticated=True, operator_id="operator-1", scopes=("report:export",)))
            verified = verify_report_bundle(root / "reports" / "report.zip", self.key)
            self.assertEqual(verified["status"], "passed")
            self.assertIn("lifecycle_receipt_audit", verified["domains"])
            self.assertEqual(result["status"], "completed")

    def test_authenticated_http_export_emits_v2_and_redacts_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt_path = root / "receipt-audit.json"
            self.receipt_file(receipt_path)
            snapshot = self.snapshot()
            executor = ReportExportActionExecutor(root / "reports", root / "audit.jsonl", signing_key=self.key, snapshot_provider=lambda: snapshot)
            server = HealthServer(port=0, session_store=object(), report_export_action_handler=executor.handle, operator_id="operator-1", operator_session_id="session-1", operator_scopes=("report:export",))
            action = ReportExportAction.sign(action_id="http-v2", operator_id="operator-1", session_id="session-1", output_name="http-v2.zip", snapshot_digest=_digest(snapshot), signing_key=self.key, receipt_audit_path=str(receipt_path))
            with server:
                request = urllib.request.Request("http://127.0.0.1:%d/api/report-export" % server.bound_port, data=json.dumps(action.to_mapping()).encode(), headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(request, timeout=2) as response:
                    payload = json.loads(response.read().decode())
                self.assertTrue(payload["ok"])
                self.assertEqual(payload["data"]["result"]["status"], "completed")
                self.assertNotIn("receipt_audit_path", json.dumps(payload))
                with urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:%d/api/sessions/session-1/events" % server.bound_port, method="GET"), timeout=2) as response:
                    events = response.read().decode()
                self.assertLess(events.index('"status":"approved"'), events.index('"status":"exporting"'))
                self.assertLess(events.index('"status":"exporting"'), events.index('"status":"completed"'))
                self.assertNotIn(str(receipt_path), events)
            self.assertIn("lifecycle_receipt_audit", verify_report_bundle(root / "reports" / "http-v2.zip", self.key)["domains"])

    def test_tampered_receipt_is_blocked_without_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt_path = root / "receipt-audit.json"
            self.receipt_file(receipt_path)
            value = json.loads(receipt_path.read_text(encoding="utf-8"))
            value["receipts"][1]["state"] = "imported"
            receipt_path.write_text(json.dumps(value), encoding="utf-8")
            snapshot = self.snapshot()
            executor = ReportExportActionExecutor(root / "reports", root / "audit.jsonl", signing_key=self.key, snapshot_provider=lambda: snapshot)
            action = ReportExportAction.sign(action_id="tampered-receipt", operator_id="operator-1", session_id="session-1", output_name="tampered.zip", snapshot_digest=_digest(snapshot), signing_key=self.key, receipt_audit_path=str(receipt_path))
            with self.assertRaisesRegex(ReportExportActionError, "export_failed:ValueError"):
                executor.handle(action, SimpleNamespace(authenticated=True, operator_id="operator-1", scopes=("report:export",)))
            self.assertFalse((root / "reports" / "tampered.zip").exists())

    def test_receipt_audit_path_is_signed_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = self.snapshot()
            executor = ReportExportActionExecutor(root / "reports", root / "audit.jsonl", signing_key=self.key, snapshot_provider=lambda: snapshot)
            action = ReportExportAction.sign(action_id="bad-receipt-path", operator_id="operator-1", session_id="session-1", output_name="report.zip", snapshot_digest=_digest(snapshot), signing_key=self.key, receipt_audit_path="relative.json")
            with self.assertRaisesRegex(ReportExportActionError, "receipt_audit_path_invalid"):
                executor.handle(action, SimpleNamespace(authenticated=True, operator_id="operator-1", scopes=("report:export",)))


if __name__ == "__main__":
    unittest.main()
