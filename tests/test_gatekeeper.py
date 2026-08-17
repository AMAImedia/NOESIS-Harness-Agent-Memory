import tempfile
import unittest
from pathlib import Path

from noesis_harness.gatekeeper import CapabilityRequest, Gatekeeper, GatekeeperError


class GatekeeperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.gate = Gatekeeper(str(Path(self.tmp.name) / "gate.jsonl"))
        self.request = CapabilityRequest(
            "sess-1", "task-1", "agent-a", "workspace.write", "write_patch", "workspace-1", "write", {"path": "notes.txt"}
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_write_requires_approval_then_commit_is_permission_only(self):
        prepared = self.gate.prepare(self.request)
        self.assertEqual(prepared.status, "waiting_approval")
        self.assertTrue(prepared.simulated["simulated"])
        approved = self.gate.approve(prepared.request_id)
        self.assertEqual(approved.status, "approved")
        committed = self.gate.commit(prepared.request_id)
        self.assertEqual(committed.status, "committed")
        self.assertIn("not_executed", committed.reason)

    def test_prepare_is_idempotent(self):
        first = self.gate.prepare(self.request)
        second = self.gate.prepare(self.request)
        self.assertEqual(first.request_id, second.request_id)
        self.assertEqual(self.gate.events.count(), 1)

    def test_read_only_capability_does_not_need_approval(self):
        request = CapabilityRequest("s", "t", "a", "memory.read", "read_memory", "scope-1", "read", {})
        decision = self.gate.prepare(request)
        self.assertEqual(decision.status, "prepared")
        self.assertEqual(self.gate.commit(decision.request_id).status, "committed")

    def test_invalid_capability_and_transition_fail_closed(self):
        with self.assertRaises(GatekeeperError):
            self.gate.prepare(CapabilityRequest("s", "t", "a", "shell.exec", "run", "x", "external", {}))
        prepared = self.gate.prepare(self.request)
        with self.assertRaises(GatekeeperError):
            self.gate.commit(prepared.request_id)
        self.gate.reject(prepared.request_id)
        with self.assertRaises(GatekeeperError):
            self.gate.approve(prepared.request_id)

    def test_sensitive_argument_keys_are_not_persisted(self):
        request = CapabilityRequest("s", "t", "a", "tool.invoke", "call", "provider", "external", {"api_key": "secret-value", "safe": "ok"})
        decision = self.gate.prepare(request)
        serialized = Path(self.tmp.name, "gate.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("secret-value", serialized)
        self.assertEqual(decision.status, "waiting_approval")


if __name__ == "__main__":
    unittest.main()
