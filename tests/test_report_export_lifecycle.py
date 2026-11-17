import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from noesis_harness.health_server import HealthServer
from noesis_harness.report_export_action import ReportExportAction, ReportExportActionExecutor, _digest


class ReportExportLifecycleTests(unittest.TestCase):
    key = b"lifecycle-signing-key-1234"

    def test_executor_lifecycle_available_then_completed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = {"local_execution": {"status": "passed"}, "native_parity": {"status": "not_run"}, "external_comparative": {"status": "not_run"}}
            executor = ReportExportActionExecutor(root / "reports", root / "audit.jsonl", signing_key=self.key, snapshot_provider=lambda: snapshot)
            self.assertEqual(executor.lifecycle_snapshot()["status"], "available")
            action = ReportExportAction.sign(action_id="life-1", operator_id="op", session_id="sess", output_name="report.zip", snapshot_digest=_digest(snapshot), signing_key=self.key)
            executor.handle(action, SimpleNamespace(authenticated=True, operator_id="op", scopes=("report:export",)))
            lifecycle = executor.lifecycle_snapshot()
            self.assertEqual(lifecycle["status"], "completed")
            self.assertFalse(lifecycle["automatic_export"])
            self.assertEqual(lifecycle["control"], "read_only")

    def test_health_projection_is_bounded_and_failure_is_blocked(self):
        server = HealthServer(report_export_lifecycle_provider=lambda: {"status": "completed", "action_id": "a", "signing_key": "secret", "automatic_export": True, "control": "write"})
        item = server.operator_snapshot()["report_export_lifecycle"]
        self.assertEqual(item["status"], "completed")
        self.assertFalse(item["automatic_export"])
        self.assertEqual(item["control"], "read_only")
        self.assertNotIn("signing_key", item)
        failed = HealthServer(report_export_lifecycle_provider=lambda: (_ for _ in ()).throw(RuntimeError("broken")))
        error = failed.telemetry_snapshot()["report_export_lifecycle"]
        self.assertEqual(error["status"], "blocked")
        self.assertFalse(error["automatic_export"])


if __name__ == "__main__":
    unittest.main()
