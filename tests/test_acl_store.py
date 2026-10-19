"""Tests for noesis_harness.acl_store.

These pin the explicit owner-scoped ACL contract ported from ``yc-software/qm``:
permissions are totally ordered, grants are owner-scoped and non-transitive,
re-grants only move upward, revocation (single and bulk) is exact, JSON
round-trips preserve authorization, and membership authorization fails closed.
"""

import unittest

from noesis_harness.acl_store import (
    AclError,
    AclStore,
    Grant,
    Membership,
    MembershipAcl,
    Permission,
)


class TestPermissionOrdering(unittest.TestCase):
    def test_permission_ordering(self):
        self.assertTrue(Permission.READ < Permission.WRITE)
        self.assertTrue(Permission.WRITE < Permission.ADMIN)
        self.assertTrue(Permission.READ < Permission.ADMIN)
        self.assertTrue(Permission.ADMIN > Permission.READ)
        self.assertTrue(Permission.READ <= Permission.READ)
        self.assertTrue(Permission.ADMIN >= Permission.WRITE)
        self.assertEqual(Permission.READ.value, "read")
        self.assertEqual(Permission.ADMIN.value, "admin")


class TestBasicAccess(unittest.TestCase):
    def setUp(self):
        self.store = AclStore()

    def test_owner_can_admin(self):
        self.store.grant("team:core", "doc:1", "user:alice", Permission.READ)
        self.assertTrue(self.store.can("team:core", "doc:1", Permission.ADMIN))
        self.assertTrue(self.store.can("team:core", "doc:1", Permission.READ))

    def test_grant_then_grantee_can_read(self):
        grant = self.store.grant("team:core", "doc:1", "user:alice", Permission.READ)
        self.assertEqual(grant.grantee_scope, "user:alice")
        self.assertEqual(grant.permission, Permission.READ)
        self.assertTrue(self.store.can("user:alice", "doc:1", Permission.READ))

    def test_grantee_cannot_exceed_permission(self):
        self.store.grant("team:core", "doc:1", "user:alice", Permission.READ)
        self.assertFalse(self.store.can("user:alice", "doc:1", Permission.WRITE))
        self.assertFalse(self.store.can("user:alice", "doc:1", Permission.ADMIN))

    def test_unknown_principal_denied(self):
        self.store.grant("team:core", "doc:1", "user:alice", Permission.ADMIN)
        self.assertFalse(self.store.can("user:bob", "doc:1", Permission.READ))
        self.assertFalse(self.store.can("user:alice", "doc:2", Permission.READ))

    def test_can_rejects_non_permission(self):
        self.store.grant("team:core", "doc:1", "user:alice", Permission.ADMIN)
        self.assertFalse(self.store.can("user:alice", "doc:1", "write"))


class TestGrantContract(unittest.TestCase):
    def setUp(self):
        self.store = AclStore()

    def test_self_grant_raises(self):
        with self.assertRaises(AclError):
            self.store.grant("user:alice", "doc:1", "user:alice", Permission.READ)

    def test_regrant_updates_upward(self):
        self.store.grant("team:core", "doc:1", "user:alice", Permission.READ)
        effective = self.store.grant(
            "team:core", "doc:1", "user:alice", Permission.WRITE
        )
        self.assertEqual(effective.permission, Permission.WRITE)
        self.assertEqual(
            self.store.permission_for("user:alice", "doc:1"), Permission.WRITE
        )

    def test_implicit_downgrade_ignored(self):
        self.store.grant("team:core", "doc:1", "user:alice", Permission.ADMIN)
        effective = self.store.grant(
            "team:core", "doc:1", "user:alice", Permission.READ
        )
        self.assertEqual(effective.permission, Permission.ADMIN)
        self.assertEqual(
            self.store.permission_for("user:alice", "doc:1"), Permission.ADMIN
        )

    def test_no_transitive_reshare(self):
        self.store.grant("team:core", "doc:1", "user:alice", Permission.ADMIN)
        with self.assertRaises(AclError):
            self.store.grant("user:alice", "doc:1", "user:bob", Permission.ADMIN)
        self.assertFalse(self.store.can("user:bob", "doc:1", Permission.READ))

    def test_grant_validation_empty_strings(self):
        with self.assertRaises(ValueError):
            Grant("", "doc:1", "user:alice", Permission.READ)
        with self.assertRaises(ValueError):
            Grant("team:core", "doc:1", "user:alice", "read")

    def test_grant_rejects_non_permission(self):
        with self.assertRaises(AclError):
            self.store.grant("team:core", "doc:1", "user:alice", "read")


class TestRevocation(unittest.TestCase):
    def setUp(self):
        self.store = AclStore()

    def test_revoke_works(self):
        self.store.grant("team:core", "doc:1", "user:alice", Permission.READ)
        self.assertTrue(self.store.revoke("team:core", "doc:1", "user:alice"))
        self.assertFalse(self.store.can("user:alice", "doc:1", Permission.READ))
        self.assertIsNone(self.store.permission_for("user:alice", "doc:1"))

    def test_revoke_absent_returns_false(self):
        self.assertFalse(self.store.revoke("team:core", "doc:1", "user:alice"))

    def test_revoke_all_for_count(self):
        self.store.grant("team:core", "doc:1", "user:alice", Permission.READ)
        self.store.grant("team:core", "doc:2", "user:alice", Permission.WRITE)
        self.store.grant("team:core", "doc:1", "user:bob", Permission.READ)
        self.assertEqual(self.store.revoke_all_for("user:alice"), 2)
        self.assertFalse(self.store.can("user:alice", "doc:1", Permission.READ))
        self.assertTrue(self.store.can("user:bob", "doc:1", Permission.READ))

    def test_owner_keeps_admin_after_revoke(self):
        self.store.grant("team:core", "doc:1", "user:alice", Permission.READ)
        self.store.revoke_all_for("user:alice")
        self.assertTrue(self.store.can("team:core", "doc:1", Permission.ADMIN))


class TestPermissionForAndEnumeration(unittest.TestCase):
    def setUp(self):
        self.store = AclStore()

    def test_permission_for(self):
        self.store.grant("team:core", "doc:1", "user:alice", Permission.WRITE)
        self.assertEqual(
            self.store.permission_for("team:core", "doc:1"), Permission.ADMIN
        )
        self.assertEqual(
            self.store.permission_for("user:alice", "doc:1"), Permission.WRITE
        )
        self.assertIsNone(self.store.permission_for("user:bob", "doc:1"))

    def test_grants_filtering_and_sorting(self):
        self.store.grant("team:core", "doc:2", "user:bob", Permission.READ)
        self.store.grant("team:core", "doc:1", "user:alice", Permission.READ)
        self.store.grant("team:core", "doc:1", "user:bob", Permission.WRITE)
        ordered = [
            (grant.owner_scope, grant.ref, grant.grantee_scope)
            for grant in self.store.grants()
        ]
        self.assertEqual(
            ordered,
            [
                ("team:core", "doc:1", "user:alice"),
                ("team:core", "doc:1", "user:bob"),
                ("team:core", "doc:2", "user:bob"),
            ],
        )
        filtered = self.store.grants(ref="doc:1")
        self.assertEqual(len(filtered), 2)
        self.assertTrue(all(grant.ref == "doc:1" for grant in filtered))

    def test_owners_and_grantees(self):
        self.store.grant("team:core", "doc:1", "user:bob", Permission.READ)
        self.store.grant("team:core", "doc:2", "user:alice", Permission.READ)
        self.store.grant("team:other", "doc:3", "user:alice", Permission.READ)
        self.assertEqual(self.store.owners(), ["team:core", "team:other"])
        self.assertEqual(self.store.grantees(), ["user:alice", "user:bob"])


class TestJsonRoundtrip(unittest.TestCase):
    def test_json_roundtrip(self):
        store = AclStore()
        store.grant("team:core", "doc:1", "user:alice", Permission.ADMIN)
        store.grant("team:core", "doc:2", "user:bob", Permission.WRITE)
        store.grant("team:other", "doc:3", "user:alice", Permission.READ)
        encoded = store.to_json()
        restored = AclStore.from_json(encoded)
        self.assertEqual(restored.to_json(), encoded)
        self.assertEqual(restored.grants(), store.grants())
        self.assertTrue(restored.can("user:alice", "doc:1", Permission.ADMIN))
        self.assertTrue(restored.can("user:bob", "doc:2", Permission.WRITE))
        self.assertTrue(restored.can("team:other", "doc:3", Permission.ADMIN))
        self.assertFalse(restored.can("user:bob", "doc:1", Permission.READ))

    def test_json_invalid_raises(self):
        with self.assertRaises(AclError):
            AclStore.from_json("not json")
        with self.assertRaises(AclError):
            AclStore.from_json('{"grants": [{"permission": "root"}]}')

    def test_json_owner_conflict_raises(self):
        payload = (
            '{"owners": {"doc:1": "team:core"},'
            ' "grants": [{"owner_scope": "team:other", "ref": "doc:1",'
            ' "grantee_scope": "user:alice", "permission": "read"}]}'
        )
        with self.assertRaises(AclError):
            AclStore.from_json(payload)


class TestMembership(unittest.TestCase):
    def test_membership_add_remove_is_member(self):
        membership = Membership()
        self.assertFalse(membership.is_member("team:core", "user:alice"))
        membership.add("team:core", "user:alice")
        membership.add("team:core", "user:alice")
        self.assertTrue(membership.is_member("team:core", "user:alice"))
        self.assertEqual(membership.members("team:core"), ["user:alice"])
        self.assertTrue(membership.remove("team:core", "user:alice"))
        self.assertFalse(membership.remove("team:core", "user:alice"))
        self.assertFalse(membership.is_member("team:core", "user:alice"))

    def test_membership_members_sorted(self):
        membership = Membership()
        membership.add("team:core", "user:carol")
        membership.add("team:core", "user:alice")
        membership.add("team:core", "user:bob")
        self.assertEqual(
            membership.members("team:core"),
            ["user:alice", "user:bob", "user:carol"],
        )
        self.assertEqual(membership.members("team:missing"), [])

    def test_membership_rejects_empty(self):
        membership = Membership()
        with self.assertRaises(ValueError):
            membership.add("", "user:alice")
        with self.assertRaises(ValueError):
            membership.add("team:core", "")


class TestMembershipAcl(unittest.TestCase):
    def _acl(self):
        acl = MembershipAcl()
        acl.grant("team:owner", "doc:1", "team:core", Permission.WRITE)
        acl.grant("team:owner", "doc:1", "user:carol", Permission.READ)
        acl._membership.add("team:core", "user:alice")
        acl._membership.add("team:core", "user:bob")
        return acl

    def test_can_member_allows_member_within_scope_permission(self):
        acl = self._acl()
        self.assertTrue(acl.can_member("team:core", "user:alice", "doc:1", Permission.READ))
        self.assertTrue(acl.can_member("team:core", "user:alice", "doc:1", Permission.WRITE))
        self.assertFalse(acl.can_member("team:core", "user:alice", "doc:1", Permission.ADMIN))

    def test_can_member_fail_closed_non_member(self):
        acl = self._acl()
        self.assertFalse(acl.can_member("team:core", "user:mallory", "doc:1", Permission.READ))

    def test_can_member_fail_closed_unknown_scope(self):
        acl = self._acl()
        self.assertFalse(acl.can_member("team:ghost", "user:alice", "doc:1", Permission.READ))

    def test_revoke_all_for_membership(self):
        acl = self._acl()
        self.assertEqual(acl.revoke_all_for("user:carol"), 1)
        self.assertFalse(acl.can("user:carol", "doc:1", Permission.READ))
        self.assertTrue(acl.can_member("team:core", "user:alice", "doc:1", Permission.READ))
        self.assertEqual(acl._membership.members("team:core"), ["user:alice", "user:bob"])


class TestDeterminism(unittest.TestCase):
    def test_determinism_regardless_of_insertion_order(self):
        first = AclStore()
        first.grant("team:a", "doc:1", "user:x", Permission.READ)
        first.grant("team:a", "doc:1", "user:y", Permission.WRITE)
        first.grant("team:a", "doc:2", "user:x", Permission.ADMIN)
        second = AclStore()
        second.grant("team:a", "doc:2", "user:x", Permission.ADMIN)
        second.grant("team:a", "doc:1", "user:y", Permission.WRITE)
        second.grant("team:a", "doc:1", "user:x", Permission.READ)
        self.assertEqual(first.grants(), second.grants())
        self.assertEqual(first.to_json(), second.to_json())
        self.assertEqual(first.to_json(), first.to_json())


if __name__ == "__main__":
    unittest.main()
