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


if __name__ == "__main__":
    unittest.main()
