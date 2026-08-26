import hashlib
import sqlite3
import hmac
import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from noesis_harness.lifecycle_audit_ingestion import LifecycleAuditIngestionAdapter, LifecycleAuditIngestionError
from noesis_harness.report_bundle import build_report_bundle
from noesis_harness.report_export_action import LIFECYCLE_SCHEMA


class LifecycleAuditIngestionTests(unittest.TestCase):
    key = b"lifecycle-ingestion-key-1234"

    def make_inputs(self, root):
        bundle = root / "bundle.zip"
        build_report_bundle(bundle, local_execution={"status": "passed"}, native_parity={"status": "not_run"}, external_comparative={"status": "not_run"}, signing_key=self.key)
        audit = root / "audit.jsonl"
        events = []
        for status in ("approved", "completed"):
            event = {"schema_version": LIFECYCLE_SCHEMA, "event_id": "a:" + status, "session_id": "s1", "action_id": "a", "status": status, "reason": "", "automatic_export": False, "control": "read_only", "created_at": 1}
            event["signature"] = hmac.new(self.key, json.dumps(event, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(), hashlib.sha256).hexdigest()
            events.append(event)
        audit.write_text("".join(json.dumps(event, sort_keys=True) + "\n" for event in events), encoding="utf-8")
        return bundle, audit

    def test_preflight_approval_import_and_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle, audit = self.make_inputs(root)
            adapter = LifecycleAuditIngestionAdapter(root / "ledger.sqlite", signing_key=self.key)
            preflight = adapter.preflight(bundle, audit)
            self.assertEqual(preflight["state"], "awaiting_approval")
            approval = adapter.approve(preflight["record_id"], operator_id="operator")
            imported = adapter.import_approved(preflight["record_id"], approval)
            self.assertEqual(imported["state"], "imported")
            self.assertFalse(imported["claim"])
            self.assertEqual(imported["receipt"]["schema_version"], "noesis.lifecycle-audit-ingestion-receipt.v1")
            self.assertTrue(imported["receipt"]["signature"])
            status = adapter.status(preflight["record_id"])
            self.assertEqual(status["last_action"]["action"], "import")
            self.assertNotIn("signing_key", json.dumps(status, sort_keys=True))
            duplicate = adapter.preflight(bundle, audit)
            self.assertEqual(duplicate["state"], "blocked")
            self.assertEqual(duplicate["reason"], "duplicate_bundle_digest")

    def test_corrupt_durable_record_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle, audit = self.make_inputs(root)
            adapter = LifecycleAuditIngestionAdapter(root / "ledger.sqlite", signing_key=self.key)
            preflight = adapter.preflight(bundle, audit)
            db = sqlite3.connect(root / "ledger.sqlite")
            try:
                with db:
                    db.execute("UPDATE lifecycle_imports SET payload=? WHERE record_id=?", ("{bad", preflight["record_id"]))
            finally:
                db.close()
            with self.assertRaisesRegex(LifecycleAuditIngestionError, "lifecycle_record_corrupt"):
                adapter.status(preflight["record_id"])

    def test_stale_tamper_and_expired_approval_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle, audit = self.make_inputs(root)
            old = time.time() - 1000
            os.utime(bundle, (old, old))
            os.utime(audit, (old, old))
            stale_adapter = LifecycleAuditIngestionAdapter(root / "ledger-stale.sqlite", signing_key=self.key, max_age_seconds=10)
            stale = stale_adapter.preflight(bundle, audit)
            self.assertEqual(stale["reason"], "evidence_stale")
            adapter = LifecycleAuditIngestionAdapter(root / "ledger-fresh.sqlite", signing_key=self.key, max_age_seconds=10)
            bundle, audit = self.make_inputs(root)
            now_stamp = time.time()
            os.utime(bundle, (now_stamp, now_stamp))
            os.utime(audit, (now_stamp, now_stamp))
            fresh = adapter.preflight(bundle, audit)
            self.assertEqual(fresh["state"], "awaiting_approval")
            approval = adapter.approve(fresh["record_id"], operator_id="operator", ttl_seconds=1, now=10)
            with self.assertRaisesRegex(LifecycleAuditIngestionError, "approval_stale_or_identity_mismatch"):
                adapter.import_approved(fresh["record_id"], approval, now=12)


if __name__ == "__main__":
    unittest.main()
