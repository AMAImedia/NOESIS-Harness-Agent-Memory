import copy
import hashlib
import hmac
import json
import tempfile
import unittest
from pathlib import Path

from noesis_harness import LifecycleAuditIngestionAdapter, verify_ingestion_receipt, verify_ingestion_receipt_audit
from noesis_harness.report_bundle import build_report_bundle
from noesis_harness.report_export_action import LIFECYCLE_SCHEMA


class LifecycleIngestionReceiptVerifierTests(unittest.TestCase):
    key = b"receipt-verifier-key-123456"

    def build_receipts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / "bundle.zip"
            build_report_bundle(bundle, local_execution={"status": "passed"}, native_parity={"status": "not_run"}, external_comparative={"status": "not_run"}, signing_key=self.key)
            audit = root / "audit.jsonl"
            events = []
            for status in ("approved", "completed"):
                event = {"schema_version": LIFECYCLE_SCHEMA, "event_id": "a:" + status, "session_id": "s1", "action_id": "a", "status": status, "reason": "", "automatic_export": False, "control": "read_only", "created_at": 1}
                event["signature"] = hmac.new(self.key, json.dumps(event, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(), hashlib.sha256).hexdigest()
                events.append(event)
            audit.write_text("".join(json.dumps(event, sort_keys=True) + "\n" for event in events), encoding="utf-8")
            adapter = LifecycleAuditIngestionAdapter(root / "ledger.sqlite", signing_key=self.key)
            preflight = adapter.preflight(bundle, audit)
            approval = adapter.approve(preflight["record_id"], operator_id="operator")
            imported = adapter.import_approved(preflight["record_id"], approval)
            return preflight["record_id"], preflight["bundle_digest"], preflight["audit_digest"], [preflight["receipt"], approval["receipt"], imported["receipt"]]

    def test_valid_audit_projection_is_claim_conservative(self):
        record, bundle, audit, receipts = self.build_receipts()
        result = verify_ingestion_receipt_audit(receipts, signing_key=self.key, record_id=record, bundle_digest=bundle, audit_digest=audit)
        self.assertEqual(result["status"], "passed")
        self.assertFalse(result["claim"])
        self.assertFalse(result["execution_claim"])
        self.assertFalse(result["comparative_claim"])

    def test_tamper_identity_duplicate_order_and_escalation_block(self):
        record, bundle, audit, receipts = self.build_receipts()
        tampered = copy.deepcopy(receipts[0])
        tampered["state"] = "imported"
        self.assertEqual(verify_ingestion_receipt(tampered, signing_key=self.key, record_id=record, bundle_digest=bundle, audit_digest=audit)["reason"], "receipt_signature_invalid")
        drift = copy.deepcopy(receipts[0])
        drift["record_id"] = "other"
        self.assertEqual(verify_ingestion_receipt(drift, signing_key=self.key, record_id=record, bundle_digest=bundle, audit_digest=audit)["reason"], "receipt_signature_invalid")
        self.assertEqual(verify_ingestion_receipt_audit(receipts + [receipts[-1]], signing_key=self.key, record_id=record, bundle_digest=bundle, audit_digest=audit)["reason"], "receipt_duplicate_action_id")
        self.assertEqual(verify_ingestion_receipt_audit([receipts[1], receipts[0], receipts[2]], signing_key=self.key, record_id=record, bundle_digest=bundle, audit_digest=audit)["reason"], "receipt_order_invalid")
        fresh_preflight = copy.deepcopy(receipts[0])
        fresh_preflight["action_id"] = "fresh-preflight"
        unsigned = {key: value for key, value in fresh_preflight.items() if key != "signature"}
        fresh_preflight["signature"] = hmac.new(self.key, json.dumps(unsigned, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(), hashlib.sha256).hexdigest()
        sequence = verify_ingestion_receipt_audit([fresh_preflight, receipts[0], receipts[1]], signing_key=self.key, record_id=record, bundle_digest=bundle, audit_digest=audit)
        self.assertEqual(sequence["reason"], "receipt_sequence_invalid")
        escalated = copy.deepcopy(receipts[0])
        escalated["claim"] = True
        self.assertEqual(verify_ingestion_receipt(escalated, signing_key=self.key, record_id=record, bundle_digest=bundle, audit_digest=audit)["reason"], "receipt_signature_invalid")

    def test_missing_receipts_is_not_run(self):
        result = verify_ingestion_receipt_audit([], signing_key=self.key, record_id="r", bundle_digest="b", audit_digest="a")
        self.assertEqual(result["status"], "not_run")
        self.assertFalse(result["claim"])


if __name__ == "__main__":
    unittest.main()
