import unittest

from noesis_harness.context_firewall import ContextFirewall, ContextItem


class ContextFirewallTests(unittest.TestCase):
    def setUp(self):
        self.firewall = ContextFirewall()

    def test_restricted_content_is_redacted_by_default(self):
        result = self.firewall.build((ContextItem("public", "safe", "public"), ContextItem("secret", "do not export", "restricted")))
        self.assertEqual(result.text, "safe")
        self.assertEqual(result.included_ids, ("public",))
        self.assertEqual(result.redacted_ids, ("secret",))
        self.assertNotIn("do not export", result.text)

    def test_scope_is_enforced_and_approval_is_explicit(self):
        item = ContextItem("remote", "approved content", "sensitive", scope="remote")
        denied = self.firewall.build((item,))
        self.assertEqual(denied.redacted_ids, ("remote",))
        approved = self.firewall.build((item,), allowed_sensitivities=("sensitive",), allowed_scopes=("remote",), explicit_approval=True)
        self.assertEqual(approved.included_ids, ("remote",))

    def test_context_budget_truncates_without_overflow(self):
        result = self.firewall.build((ContextItem("a", "12345", "public"), ContextItem("b", "67890", "public")), max_chars=7)
        self.assertLessEqual(len(result.text), 7)
        self.assertIn("a", result.included_ids)
        self.assertIn("b", result.truncated_ids)

    def test_mixed_scope_ordering_redacts_only_blocked_items(self):
        items = (
            ContextItem("public-a", "A", "public", resource_id="res-a"),
            ContextItem("remote-secret", "SECRET", "sensitive", scope="remote", resource_id="res-secret"),
            ContextItem("public-b", "B", "public", resource_id="res-b"),
        )
        result = self.firewall.build(items)
        self.assertEqual(result.included_ids, ("public-a", "public-b"))
        self.assertEqual(result.included_resource_ids, ("res-a", "res-b"))
        self.assertEqual(result.redacted_ids, ("remote-secret",))
        self.assertEqual(result.digest, self.firewall.build(items).digest)
        self.assertNotIn("SECRET", result.text)

    def test_explicit_approval_includes_restricted_item_and_preserves_provenance(self):
        item = ContextItem("restricted", "approved", "restricted", scope="vault", resource_id="vault-7")
        result = self.firewall.build((item,), allowed_sensitivities=("restricted",), allowed_scopes=("local",), explicit_approval=True)
        self.assertEqual(result.included_ids, ("restricted",))
        self.assertEqual(result.included_resource_ids, ("vault-7",))

    def test_invalid_scope_configuration_fails_closed(self):
        with self.assertRaises(ValueError):
            self.firewall.build((ContextItem("a", "x", "public"),), allowed_scopes=())
        with self.assertRaises(ValueError):
            self.firewall.build((ContextItem("a", "x", "public", scope=""),))


if __name__ == "__main__":
    unittest.main()
