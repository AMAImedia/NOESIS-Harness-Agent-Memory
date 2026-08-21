import tempfile
import unittest

from noesis_harness.admin_migration import OperatorMigrationModeSource
from noesis_harness.admin_state_sqlite import SQLiteAdminStateError, SQLiteAdministrativeBackend
from noesis_harness.promotion_integration import OperatorAuthContext


class SQLiteAdministrativeBackendTests(unittest.TestCase):
    def backend(self):
        return SQLiteAdministrativeBackend(tempfile.mktemp(suffix=".sqlite3"), signing_key=b"sqlite-admin-signing-key", admin_ids=("admin-1",))

    def provision_admin(self, backend):
        backend.bootstrap_session("admin-1", "admin-session", ttl_seconds=600, scopes=("admin:reviewers", "admin:session"))

    def test_single_store_grant_and_audit_commit_atomically(self):
        backend = self.backend()
        self.provision_admin(backend)
        result = backend.grant_reviewer(admin_id="admin-1", admin_session_id="admin-session", target_operator_id="reviewer-1", target_session_id="reviewer-session", scopes=("promotion:review",), action_id="grant-1")
        receipt = result["audit_receipt"]
        self.assertTrue(backend.verify_receipt(receipt))
        self.assertEqual(backend.audit("grant-1")["new_state"], "active")
        self.assertEqual(backend.audit("grant-1")["action_id"], "grant-1")

    def test_conflict_and_denial_are_transactionally_fail_closed(self):
        backend = self.backend()
        self.provision_admin(backend)
        backend.grant_reviewer(admin_id="admin-1", admin_session_id="admin-session", target_operator_id="reviewer-1", target_session_id="reviewer-session", scopes=("promotion:review",), action_id="grant-1")
        with self.assertRaisesRegex(SQLiteAdminStateError, "administrative_policy_conflict"):
            backend.grant_reviewer(admin_id="admin-1", admin_session_id="admin-session", target_operator_id="reviewer-1", target_session_id="reviewer-session", scopes=("promotion:review",), action_id="grant-2")
        self.assertIsNone(backend.audit("grant-2"))
        with self.assertRaisesRegex(SQLiteAdminStateError, "administrative_policy_denied"):
            backend.grant_reviewer(admin_id="intruder", admin_session_id="admin-session", target_operator_id="reviewer-2", target_session_id="session-2", scopes=("promotion:review",), action_id="grant-3")
        self.assertIsNone(backend.audit("grant-3"))

    def test_session_open_close_and_recovery_from_reopen(self):
        path = tempfile.mktemp(suffix=".sqlite3")
        backend = SQLiteAdministrativeBackend(path, signing_key=b"sqlite-admin-signing-key", admin_ids=("admin-1",))
        backend.bootstrap_session("admin-1", "admin-session", ttl_seconds=600, scopes=("admin:reviewers", "admin:session"))
        opened = backend.open_session(actor_id="admin-1", actor_session_id="admin-session", target_operator_id="reviewer-1", target_session_id="reviewer-session", ttl_seconds=300, scopes=("promotion:review",), action_id="open-1")
        self.assertTrue(backend.verify_receipt(opened["audit_receipt"]))
        reopened = SQLiteAdministrativeBackend(path, signing_key=b"sqlite-admin-signing-key", admin_ids=("admin-1",))
        with self.assertRaisesRegex(SQLiteAdminStateError, "operator_session_conflict"):
            reopened.open_session(actor_id="admin-1", actor_session_id="admin-session", target_operator_id="reviewer-1", target_session_id="reviewer-session", ttl_seconds=300, scopes=("promotion:review",), action_id="open-2")
        closed = reopened.close_session(actor_id="admin-1", actor_session_id="admin-session", target_session_id="reviewer-session", action_id="close-1")
        self.assertFalse(closed["active"])
        self.assertTrue(reopened.verify_receipt(closed["audit_receipt"]))

    def test_mode_receipt_replay_is_idempotent_but_tamper_fails_closed(self):
        key = b"sqlite-mode-replay-key"
        path = tempfile.mktemp(suffix=".sqlite3")
        backend = SQLiteAdministrativeBackend(path, signing_key=key, admin_ids=("operator-1",))
        source = OperatorMigrationModeSource(tempfile.mktemp(), operator_ids=("operator-1",), signing_key=key, audit_backend=backend)
        context = OperatorAuthContext("operator-1", "operator-session", ("admin:migration",))
        receipt = source.handle_action({"schema_version": "noesis.migration-mode-action.v1", "action_id": "mode-replay-1", "action": "set_mode", "mode": "dual_read", "operator_id": "operator-1", "reason": "replay test"}, context)
        self.assertEqual(backend.record_mode_change_receipt(receipt)["action_id"], "mode-replay-1")
        tampered = dict(receipt)
        tampered["reason"] = "changed"
        tampered["signed_receipt"] = source._sign({key: value for key, value in tampered.items() if key != "signed_receipt"})
        with self.assertRaisesRegex(SQLiteAdminStateError, "migration_receipt_replay_conflict"):
            backend.record_mode_change_receipt(tampered)

    def test_failed_transaction_does_not_leave_audit_without_state(self):
        backend = self.backend()
        self.provision_admin(backend)
        with self.assertRaisesRegex(SQLiteAdminStateError, "operator_session_inactive_or_expired"):
            backend.open_session(actor_id="admin-1", actor_session_id="missing", target_operator_id="reviewer-1", target_session_id="reviewer-session", action_id="open-denied")
        self.assertIsNone(backend.audit("open-denied"))


if __name__ == "__main__":
    unittest.main()

__all__ = ["SQLiteAdministrativeBackendTests"]

