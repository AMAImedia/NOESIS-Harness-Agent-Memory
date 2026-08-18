import tempfile
import unittest

from noesis_harness.admin_migration import AdministrativeMigrationAdapter, AdministrativeMigrationError
from noesis_harness.admin_state_sqlite import SQLiteAdministrativeBackend
from noesis_harness.promotion_integration import ReviewerAuthorizationStore, OperatorSessionRegistry


class AdministrativeMigrationAdapterTests(unittest.TestCase):
    def make(self):
        legacy_sessions = OperatorSessionRegistry(tempfile.mktemp())
        legacy_reviewer = ReviewerAuthorizationStore(tempfile.mktemp())
        sqlite = SQLiteAdministrativeBackend(tempfile.mktemp(), signing_key=b'migration-signing-key', admin_ids=('admin-1',))
        sqlite.bootstrap_session('admin-1', 'admin-session', scopes=('admin:reviewers', 'admin:session'))
        legacy_sessions.open('admin-1', 'admin-session', ttl_seconds=900, scopes=('admin:reviewers', 'admin:session'))
        adapter = AdministrativeMigrationAdapter(tempfile.mktemp(), legacy_reviewer=legacy_reviewer, legacy_sessions=legacy_sessions, sqlite_backend=sqlite)
        return adapter, legacy_sessions, legacy_reviewer, sqlite

    def test_legacy_to_dual_read_is_explicit_and_mismatch_blocks(self):
        adapter, *_ = self.make()
        self.assertEqual(adapter.mode, 'legacy')
        adapter.start('dual_read', operator_id='admin-1', reason='verify before adoption')
        adapter.legacy_reviewer.grant('reviewer-1', 'reviewer-session', ('promotion:review',))
        check = adapter.verify_dual_read(session_id='admin-session', reviewer_operator_id='reviewer-1', reviewer_session_id='reviewer-session')
        self.assertEqual(check.status, 'blocked')
        with self.assertRaisesRegex(AdministrativeMigrationError, 'dual_read_state_mismatch'):
            adapter.require_dual_read(session_id='admin-session', reviewer_operator_id='reviewer-1', reviewer_session_id='reviewer-session')

    def test_sqlite_mode_requires_dual_read_and_rollback_is_explicit(self):
        adapter, *_ = self.make()
        with self.assertRaisesRegex(AdministrativeMigrationError, 'sqlite_mode_requires_dual_read'):
            adapter.start('sqlite', operator_id='admin-1', reason='unsafe direct cutover')
        adapter.start('dual_read', operator_id='admin-1', reason='dual read')
        adapter.start('sqlite', operator_id='admin-1', reason='verified migration')
        self.assertEqual(adapter.mode, 'sqlite')
        plan = adapter.plan(session_id='admin-session', reviewer_operator_id='reviewer-1', reviewer_session_id='reviewer-session')
        self.assertFalse(plan['automatic_cutover'])
        rollback = adapter.rollback(operator_id='admin-1', reason='operator requested rollback')
        self.assertEqual(rollback['mode'], 'legacy')
        self.assertEqual(adapter.mode, 'legacy')

    def test_dual_read_passes_when_projections_match(self):
        adapter, legacy_sessions, legacy_reviewer, sqlite = self.make()
        legacy_sessions.open('reviewer-1', 'reviewer-session', ttl_seconds=900, scopes=('promotion:review',))
        sqlite.open_session(actor_id='admin-1', actor_session_id='admin-session', target_operator_id='reviewer-1', target_session_id='reviewer-session', ttl_seconds=900, scopes=('promotion:review',), action_id='open-reviewer')
        legacy_reviewer.grant('reviewer-1', 'reviewer-session', ('promotion:review',))
        sqlite.grant_reviewer(admin_id='admin-1', admin_session_id='admin-session', target_operator_id='reviewer-1', target_session_id='reviewer-session', scopes=('promotion:review',), action_id='grant-reviewer')
        adapter.start('dual_read', operator_id='admin-1', reason='verified projections')
        check = adapter.verify_dual_read(session_id='reviewer-session', reviewer_operator_id='reviewer-1', reviewer_session_id='reviewer-session')
        self.assertEqual(check.status, 'passed')
        self.assertTrue(check.session_match)
        self.assertTrue(check.reviewer_match)


if __name__ == '__main__':
    unittest.main()

__all__ = ['AdministrativeMigrationAdapterTests']
