import hashlib
import hmac
import json
import tempfile
import unittest
from pathlib import Path

from noesis_harness.report_export_action import LIFECYCLE_SCHEMA
from noesis_harness.report_export_lifecycle import lifecycle_audit_only_projection, verify_lifecycle_events, verify_lifecycle_file


class LifecycleVerifierTests(unittest.TestCase):
    key = b"lifecycle-verifier-key-1234"

    def event(self, action, status, session="session-1", reason=""):
        value = {"schema_version": LIFECYCLE_SCHEMA, "event_id": action + ":" + status, "session_id": session, "action_id": action, "status": status, "reason": reason, "automatic_export": False, "control": "read_only", "created_at": 1}
        value["signature"] = hmac.new(self.key, json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(), hashlib.sha256).hexdigest()
        return value

    def test_valid_order_is_audit_only(self):
        result = verify_lifecycle_events([self.event("a", "approved"), self.event("a", "exporting"), self.event("a", "completed")], self.key)
        self.assertEqual(result["status"], "passed")
        projection = lifecycle_audit_only_projection(result)
        self.assertFalse(projection["claim"])
        self.assertFalse(projection["execution_claim"])
        self.assertFalse(projection["comparative_claim"])

    def test_tamper_duplicate_and_order_block(self):
        valid = [self.event("a", "approved"), self.event("a", "completed")]
        tampered = [dict(valid[0]), valid[1]]
        tampered[0]["status"] = "exporting"
        self.assertEqual(verify_lifecycle_events(tampered, self.key)["reason"], "lifecycle_signature_invalid")
        duplicate = [valid[0], valid[0]]
        self.assertEqual(verify_lifecycle_events(duplicate, self.key)["reason"], "duplicate_lifecycle_event_id")
        invalid_order = [self.event("b", "exporting"), self.event("b", "completed")]
        self.assertEqual(verify_lifecycle_events(invalid_order, self.key)["reason"], "lifecycle_order_invalid")

    def test_file_import_and_cross_session_groups(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lifecycle.jsonl"
            events = [self.event("a", "approved", "s1"), self.event("a", "completed", "s1"), self.event("b", "approved", "s2"), self.event("b", "blocked", "s2", "provider")]
            path.write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in events), encoding="utf-8")
            self.assertEqual(verify_lifecycle_file(path, self.key)["status"], "passed")
            self.assertEqual(verify_lifecycle_events([], self.key)["status"], "not_run")


if __name__ == "__main__":
    unittest.main()
