import hashlib
import hmac
import json
import tempfile
import unittest
from pathlib import Path

from noesis_harness import HealthServer, LifecycleAuditIngestionAdapter, build_healthserver_wiring
from noesis_harness.report_bundle import build_report_bundle
from noesis_harness.report_export_action import LIFECYCLE_SCHEMA


class LifecycleIngestionWiringTests(unittest.TestCase):
    key = b"wiring-test-key-123456789"

    def make_inputs(self, root):
        bundle = root / "bundle.zip"
        build_report_bundle(bundle, local_execution={"status": "passed"}, native_parity={"status": "not_run"}, external_comparative={"status": "not_run"}, signing_key=self.key)
        audit = root / "audit.jsonl"
        event = {"schema_version": LIFECYCLE_SCHEMA, "event_id": "a:approved", "session_id": "s", "action_id": "a", "status": "approved", "reason": "", "automatic_export": False, "control": "read_only", "created_at": 1}
        event["signature"] = hmac.new(self.key, json.dumps(event, sort_keys=True, separators=(",", ":")).encode(), hashlib.sha256).hexdigest()
        event2 = dict(event, event_id="a:completed", status="completed")
        event2["signature"] = hmac.new(self.key, json.dumps({k: v for k, v in event2.items() if k != "signature"}, sort_keys=True, separators=(",", ":")).encode(), hashlib.sha256).hexdigest()
        audit.write_text(json.dumps(event, sort_keys=True) + "\n" + json.dumps(event2, sort_keys=True) + "\n", encoding="utf-8")
        return bundle, audit

    def test_standard_wiring_lifecycle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle, audit = self.make_inputs(root)
            adapter = LifecycleAuditIngestionAdapter(root / "ledger.sqlite", signing_key=self.key)
            status, action = build_healthserver_wiring(adapter)
            preflight = action({"action": "preflight", "bundle_path": str(bundle), "lifecycle_path": str(audit)}, type("Context", (), {"operator_id": "operator"})())
            self.assertEqual(preflight["state"], "awaiting_approval")
            approval = action({"action": "approve", "record_id": preflight["record_id"]}, type("Context", (), {"operator_id": "operator"})())
            imported = action({"action": "import", "record_id": preflight["record_id"], "approval": approval["approval"]}, type("Context", (), {"operator_id": "operator"})())
            self.assertEqual(imported["state"], "imported")
            self.assertFalse(imported["claim"])
            self.assertEqual(status()["state"], "imported")

    def test_absolute_existing_paths_required(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            adapter = LifecycleAuditIngestionAdapter(root / "ledger.sqlite", signing_key=self.key)
            _, action = build_healthserver_wiring(adapter)
            with self.assertRaisesRegex(ValueError, "input_paths_must_be_existing_absolute_files"):
                action({"action": "preflight", "bundle_path": "../bundle.zip", "lifecycle_path": "../audit.jsonl"}, type("Context", (), {"operator_id": "operator"})())


if __name__ == "__main__":
    unittest.main()
