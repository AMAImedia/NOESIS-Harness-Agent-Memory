import tempfile
import unittest

from noesis_harness.delegated_resume import DelegatedResumeError, DelegatedResumeStore


class DelegatedResumeTests(unittest.TestCase):
    def _store(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        return DelegatedResumeStore(directory.name + "/delegations.jsonl")

    def test_resume_requires_fresh_approval_and_consumes_once(self):
        store = self._store()
        identity = store.create("session-1", "task-1", "agent-a", "/workspace/a", ("read", "write"), delegation_id="d-1")
        store.checkpoint("d-1", "step-1")
        store.mark_interrupted("d-1")
        approval = store.approve_resume("d-1", "operator-approval-1")
        resumed = store.consume_resume_approval("d-1", approval, request_digest=identity.request_digest)
        self.assertEqual(resumed.state, "resuming")
        with self.assertRaisesRegex(DelegatedResumeError, "resume_approval_replayed"):
            store.consume_resume_approval("d-1", approval, request_digest=identity.request_digest)

    def test_request_mutation_is_rejected(self):
        store = self._store()
        identity = store.create("session-1", "task-1", "agent-a", "/workspace/a", ("read",), delegation_id="d-2")
        store.mark_interrupted("d-2")
        approval = store.approve_resume("d-2", "operator-approval-2")
        with self.assertRaisesRegex(DelegatedResumeError, "delegation_request_mutated"):
            store.consume_resume_approval("d-2", approval, request_digest="0" * 64)
        with self.assertRaisesRegex(DelegatedResumeError, "delegation_identity_immutable"):
            store.create("session-1", "task-1", "agent-a", "/other", ("read",), delegation_id="d-2")
        self.assertEqual(store.identity("d-2").request_digest, identity.request_digest)

    def test_checkpoint_drift_invalidates_approval(self):
        store = self._store()
        identity = store.create("session-1", "task-1", "agent-a", "/workspace/a", ("read",), delegation_id="d-3")
        store.checkpoint("d-3", "step-1")
        store.mark_interrupted("d-3")
        approval = store.approve_resume("d-3", "operator-approval-3")
        store.checkpoint("d-3", "step-2")
        with self.assertRaisesRegex(DelegatedResumeError, "resume_checkpoint_drift"):
            store.consume_resume_approval("d-3", approval, request_digest=identity.request_digest)

    def test_terminal_delegation_cannot_checkpoint_or_resume(self):
        store = self._store()
        store.create("session-1", "task-1", "agent-a", "/workspace/a", ("read",), delegation_id="d-4")
        store.complete("d-4")
        with self.assertRaisesRegex(DelegatedResumeError, "terminal_delegation_not_checkpointable"):
            store.checkpoint("d-4", "late")
        with self.assertRaisesRegex(DelegatedResumeError, "fresh_resume_approval_required"):
            store.approve_resume("d-4", "operator-approval-4")


if __name__ == "__main__":
    unittest.main()
