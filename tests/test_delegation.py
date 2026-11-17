import tempfile
import unittest
from pathlib import Path

from noesis_harness.delegation import DelegationCoordinator, DelegationError, DelegationRequest


class DelegationTests(unittest.TestCase):
    def test_review_only_delegation_isolated_and_signed(self):
        with tempfile.TemporaryDirectory() as root:
            coordinator = DelegationCoordinator(root, b"delegation-test-key-2026")
            request = DelegationRequest("delegation-1", "session-1", "task-1", "agent-1")

            def callback(context):
                context.path("artifact.txt").write_text("review-only\n", encoding="utf-8")
                return {"status": "fixture_only", "artifact": "artifact.txt"}

            receipt, result = coordinator.delegate(request, callback)
            self.assertEqual(result.status, "passed")
            self.assertEqual(receipt.status, "passed")
            self.assertTrue(coordinator.verify(receipt))
            self.assertTrue((Path(receipt.workspace) / "artifact.txt").is_file())
            self.assertTrue((Path(receipt.workspace) / "DELEGATION_RECEIPT.json").is_file())
            self.assertNotEqual(receipt.artifact_digest, "")

    def test_write_capability_requires_explicit_approval(self):
        with tempfile.TemporaryDirectory() as root:
            coordinator = DelegationCoordinator(root, b"delegation-test-key-2026")
            request = DelegationRequest("delegation-2", "session-1", "task-2", "agent-2", ("read", "workspace_write"), False)
            with self.assertRaisesRegex(DelegationError, "capability_approval_required"):
                coordinator.delegate(request, lambda context: None)

    def test_denied_capability_and_tampered_receipt_fail_closed(self):
        with tempfile.TemporaryDirectory() as root:
            coordinator = DelegationCoordinator(root, b"delegation-test-key-2026")
            denied = DelegationRequest("delegation-3", "session-1", "task-3", "agent-3", ("read", "secret_read"))
            with self.assertRaisesRegex(DelegationError, "capability_denied"):
                coordinator.delegate(denied, lambda context: None)
            request = DelegationRequest("delegation-4", "session-1", "task-4", "agent-4")
            receipt, _ = coordinator.delegate(request, lambda context: {"fixture": True})
            tampered = type(receipt)(receipt.delegation_id, receipt.session_id, receipt.task_id, receipt.agent_id, receipt.workspace, receipt.capabilities, "failed", receipt.artifact_digest, receipt.output_digest, receipt.signed_receipt)
            self.assertFalse(coordinator.verify(tampered))


if __name__ == "__main__":
    unittest.main()
