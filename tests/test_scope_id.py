"""Tests for noesis_harness.scope_id.

These pin the scope namespace contract ported from ``yc-software/qm``:
parsing/formatting is strict, storage keys are filesystem-safe, workspace
layers are deterministic, and the audience predicate fails closed.
"""

import unittest

from noesis_harness.scope_id import (
    SCOPE_KINDS,
    ScopeError,
    WorkspaceLayer,
    conversation_scope,
    format_scope,
    is_cross_scope,
    is_entitled,
    layered_workspace,
    parse_scope,
    personal_scope,
    scope_key,
)


class TestParseFormat(unittest.TestCase):
    def test_parse_format_roundtrip(self):
        self.assertEqual(parse_scope("personal:alice"), ("personal", "alice"))
        self.assertEqual(parse_scope("channel:general"), ("channel", "general"))
        self.assertEqual(parse_scope("group:room-7"), ("group", "room-7"))
        for kind in SCOPE_KINDS:
            self.assertEqual(format_scope(kind, "ref"), kind + ":ref")
            self.assertEqual(parse_scope(format_scope(kind, "ref")), (kind, "ref"))

    def test_parse_invalid_kind_raises(self):
        with self.assertRaises(ScopeError):
            parse_scope("planet:mars")
        with self.assertRaises(ScopeError):
            format_scope("planet", "mars")

    def test_parse_empty_ref_raises(self):
        with self.assertRaises(ScopeError):
            parse_scope("personal:")
        with self.assertRaises(ScopeError):
            format_scope("personal", "")

    def test_parse_ref_with_colon_raises(self):
        with self.assertRaises(ScopeError):
            parse_scope("personal:a:b")
        with self.assertRaises(ScopeError):
            format_scope("personal", "a:b")

    def test_parse_missing_colon_raises(self):
        with self.assertRaises(ScopeError):
            parse_scope("personal")


class TestPersonalAndConversation(unittest.TestCase):
    def test_personal_scope(self):
        self.assertEqual(personal_scope("alice"), "personal:alice")

    def test_personal_scope_empty_actor_raises(self):
        with self.assertRaises(ScopeError):
            personal_scope("")

    def test_conversation_scope_dm(self):
        self.assertEqual(
            conversation_scope("alice", room="group:red", is_dm=True),
            "personal:alice",
        )

    def test_conversation_scope_no_room(self):
        self.assertEqual(conversation_scope("alice"), "personal:alice")
        self.assertEqual(conversation_scope("alice", room=""), "personal:alice")

    def test_conversation_scope_hash_room_is_channel(self):
        self.assertEqual(
            conversation_scope("alice", room="#general"),
            "channel:general",
        )

    def test_conversation_scope_channel_prefix_is_channel(self):
        self.assertEqual(
            conversation_scope("alice", room="channel:support"),
            "channel:support",
        )

    def test_conversation_scope_group(self):
        self.assertEqual(
            conversation_scope("alice", room="standup"),
            "group:standup",
        )

    def test_conversation_scope_empty_actor_raises(self):
        with self.assertRaises(ScopeError):
            conversation_scope("", room="standup")


class TestScopeKey(unittest.TestCase):
    def test_scope_key_safe_passthrough(self):
        self.assertEqual(scope_key("personal:alice"), "personal-alice")
        self.assertEqual(scope_key("group:room-7.A"), "group-room-7.A")

    def test_scope_key_hashes_unsafe_ref(self):
        key = scope_key("personal:alice smith")
        self.assertTrue(key.startswith("personal-"))
        suffix = key[len("personal-"):]
        self.assertEqual(len(suffix), 16)
        int(suffix, 16)
        self.assertNotEqual(key, "personal-alice smith")
        self.assertNotEqual(key, scope_key("personal:bob smith"))

    def test_scope_key_hashes_long_ref(self):
        key = scope_key(format_scope("team", "a" * 65))
        self.assertEqual(len(key[len("team-"):]), 16)

    def test_scope_key_no_separators_or_dotdot(self):
        for ref in ("a/../../b", "..", "a..b", "/etc/passwd", "a b"):
            key = scope_key(format_scope("group", ref))
            self.assertNotIn("/", key)
            self.assertNotIn("\\", key)
            self.assertNotIn("..", key)
            self.assertFalse(key.startswith("/"))


class TestWorkspaceLayer(unittest.TestCase):
    def test_invalid_mode_raises(self):
        with self.assertRaises(ScopeError):
            WorkspaceLayer("personal:alice", "personal-alice", "rwx")

    def test_valid_modes(self):
        self.assertEqual(
            WorkspaceLayer("personal:alice", "personal-alice", "rw").mode, "rw"
        )
        self.assertEqual(
            WorkspaceLayer("org:acme", "org-acme", "ro").mode, "ro"
        )

    def test_layered_workspace_order_and_modes(self):
        layers = layered_workspace(
            "personal:alice", org="org:acme", team="team:red"
        )
        self.assertEqual(
            [layer.scope_id for layer in layers],
            ["org:acme", "personal:alice", "team:red"],
        )
        self.assertEqual([layer.mode for layer in layers], ["ro", "rw", "ro"])
        self.assertEqual(
            [layer.mount_path for layer in layers],
            ["org-acme", "personal-alice", "team-red"],
        )

    def test_layered_workspace_bare_refs_namespaced(self):
        layers = layered_workspace("personal:alice", org="acme", team="red")
        self.assertEqual(
            [layer.scope_id for layer in layers],
            ["org:acme", "personal:alice", "team:red"],
        )

    def test_layered_workspace_dm_omits_team(self):
        layers = layered_workspace(
            "personal:alice", org="org:acme", team="team:red", is_dm=True
        )
        self.assertEqual(
            [layer.scope_id for layer in layers],
            ["org:acme", "personal:alice"],
        )

    def test_layered_workspace_no_org(self):
        layers = layered_workspace("personal:alice")
        self.assertEqual(len(layers), 1)
        self.assertEqual(layers[0].mode, "rw")


class TestEntitlement(unittest.TestCase):
    def test_personal_owner_visible(self):
        self.assertTrue(
            is_entitled("personal:alice", "personal:alice", "personal:alice")
        )

    def test_personal_other_not_visible(self):
        self.assertFalse(
            is_entitled("personal:bob", "personal:alice", "personal:bob")
        )
        self.assertFalse(
            is_entitled("channel:general", "personal:alice", "channel:general")
        )

    def test_channel_match_visible_by_scope(self):
        self.assertTrue(
            is_entitled("channel:general", "channel:general", "")
        )
        self.assertFalse(
            is_entitled("group:general", "channel:general", "")
        )

    def test_channel_visible_by_session_scope(self):
        self.assertTrue(
            is_entitled("personal:alice", "channel:general", "channel:general")
        )
        self.assertFalse(
            is_entitled("personal:alice", "channel:general", "channel:other")
        )

    def test_org_team_labels_visible(self):
        self.assertTrue(is_entitled("personal:alice", "org:acme", ""))
        self.assertTrue(is_entitled("personal:alice", "team:red", ""))

    def test_malformed_entitlement_fails_closed(self):
        self.assertFalse(is_entitled("nope", "personal:alice", "personal:alice"))
        self.assertFalse(is_entitled("personal:alice", "nope", "personal:alice"))
        self.assertFalse(is_entitled("personal:alice", "personal:", "personal:alice"))

    def test_is_cross_scope(self):
        self.assertFalse(is_cross_scope("personal:alice", "personal:alice"))
        self.assertTrue(is_cross_scope("personal:alice", "personal:bob"))
        self.assertTrue(is_cross_scope("channel:x", "group:x"))
        self.assertTrue(is_cross_scope("personal:alice", "not-a-scope"))


if __name__ == "__main__":
    unittest.main()
