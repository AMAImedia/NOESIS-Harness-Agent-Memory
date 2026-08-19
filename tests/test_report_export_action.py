import json
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace

from noesis_harness.health_server import HealthServer
from noesis_harness.report_export_action import ReportExportAction, ReportExportActionError, ReportExportActionExecutor
from noesis_harness.report_bundle import verify_report_bundle
from noesis_harness.report_export_action import _digest


class ReportExportActionTests(unittest.TestCase):
    key = b"report-export-action-key-1234"

    def snapshot(self):
        return {"local_execution": {"status": "passed"}, "native_parity": {"status": "not_run"}, "external_comparative": {"status": "not_run"}}

    def test_handler_exports_once_and_writes_signed_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = self.snapshot()
            executor = ReportExportActionExecutor(root / "reports", root / "audit.jsonl", signing_key=self.key, snapshot_provider=lambda: snapshot)
            action = ReportExportAction.sign(action_id="export-1", operator_id="operator-1", session_id="session-1", output_name="report.zip", snapshot_digest=_digest(snapshot), signing_key=self.key)
            context = SimpleNamespace(authenticated=True, operator_id="operator-1", scopes=("report:export",))
            result = executor.handle(action, context)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(verify_report_bundle(root / "reports" / "report.zip", self.key)["status"], "passed")
            with self.assertRaisesRegex(ReportExportActionError, "action_replayed"):
                executor.handle(action, context)
            self.assertEqual(len(root.joinpath("audit.jsonl").read_text(encoding="utf-8").splitlines()), 1)

    def test_tamper_scope_digest_and_path_fail_before_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = self.snapshot()
            executor = ReportExportActionExecutor(root / "reports", root / "audit.jsonl", signing_key=self.key, snapshot_provider=lambda: snapshot)
            context = SimpleNamespace(authenticated=True, operator_id="operator-1", scopes=("report:export",))
            bad_signature = ReportExportAction("a1", "operator-1", "s1", "a.zip", _digest(snapshot), "bad")
            with self.assertRaisesRegex(ReportExportActionError, "signature_invalid"):
                executor.handle(bad_signature, context)
            action = ReportExportAction.sign(action_id="a2", operator_id="operator-1", session_id="s1", output_name="../escape.zip", snapshot_digest=_digest(snapshot), signing_key=self.key)
            with self.assertRaisesRegex(ReportExportActionError, "output_name_invalid"):
                executor.handle(action, context)
            action = ReportExportAction.sign(action_id="a3", operator_id="operator-1", session_id="s1", output_name="ok.zip", snapshot_digest="0" * 64, signing_key=self.key)
            with self.assertRaisesRegex(ReportExportActionError, "snapshot_digest_drift"):
                executor.handle(action, context)
            with self.assertRaisesRegex(ReportExportActionError, "scope_required"):
                executor.handle(ReportExportAction.sign(action_id="a4", operator_id="operator-1", session_id="s1", output_name="ok.zip", snapshot_digest=_digest(snapshot), signing_key=self.key), SimpleNamespace(authenticated=True, operator_id="operator-1", scopes=()))

    def test_authenticated_http_endpoint_emits_ordered_sse_lifecycle_events(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = self.snapshot()
            executor = ReportExportActionExecutor(root / "reports", root / "audit.jsonl", signing_key=self.key, snapshot_provider=lambda: snapshot)
            server = HealthServer(port=0, session_store=object(), report_export_action_handler=executor.handle, operator_id="operator-1", operator_session_id="session-1", operator_scopes=("report:export",))
            action = ReportExportAction.sign(action_id="sse-1", operator_id="operator-1", session_id="session-1", output_name="sse.zip", snapshot_digest=_digest(snapshot), signing_key=self.key)
            with server:
                request = urllib.request.Request("http://127.0.0.1:%d/api/report-export" % server.bound_port, data=json.dumps(action.to_mapping()).encode(), headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(request, timeout=2):
                    pass
                with urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:%d/api/sessions/session-1/events" % server.bound_port, method="GET"), timeout=2) as response:
                    body = response.read().decode()
                self.assertLess(body.index('"status":"approved"'), body.index('"status":"exporting"'))
                self.assertLess(body.index('"status":"exporting"'), body.index('"status":"completed"'))
                self.assertIn('"automatic_export":false', body)
                self.assertIn('"control":"read_only"', body)
                self.assertNotIn("signing_key", body)

    def test_authenticated_http_endpoint_dispatches_and_redacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = self.snapshot()
            executor = ReportExportActionExecutor(root / "reports", root / "audit.jsonl", signing_key=self.key, snapshot_provider=lambda: snapshot)
            server = HealthServer(port=0, report_export_action_handler=executor.handle, operator_id="operator-1", operator_session_id="session-1", operator_scopes=("report:export",))
            action = ReportExportAction.sign(action_id="http-1", operator_id="operator-1", session_id="session-1", output_name="http.zip", snapshot_digest=_digest(snapshot), signing_key=self.key)
            with server:
                request = urllib.request.Request("http://127.0.0.1:%d/api/report-export" % server.bound_port, data=json.dumps(action.to_mapping()).encode(), headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(request, timeout=2) as response:
                    payload = json.loads(response.read().decode())
                self.assertEqual(payload["ok"], True)
                self.assertEqual(payload["data"]["result"]["status"], "completed")
                self.assertNotIn("signing_key", payload["data"]["result"])


if __name__ == "__main__":
    unittest.main()
