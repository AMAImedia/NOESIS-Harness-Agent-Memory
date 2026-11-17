from __future__ import annotations

import unittest

from noesis_harness.authorization_gate import (
    AuthorizationGate,
    Decision,
    RiskTier,
    Rule,
    pattern_matches,
)


class PatternMatchesTests(unittest.TestCase):
    def test_exact_match_is_case_sensitive(self):
        self.assertTrue(pattern_matches("Read(file)", "Read(file)"))
        self.assertFalse(pattern_matches("Read(file)", "read(file)"))
        self.assertFalse(pattern_matches("Read(file)", "Read(other)"))

    def test_trailing_wildcard_is_prefix_match(self):
        self.assertTrue(pattern_matches("Bash(git commit *)", "Bash(git commit -m x)"))
        self.assertTrue(pattern_matches("Bash(npm:*)", "Bash(npm:install)"))
        self.assertFalse(pattern_matches("Bash(git commit *)", "Bash(git push)"))

    def test_bare_wildcard_matches_everything(self):
        self.assertTrue(pattern_matches("*", "anything at all"))
        self.assertTrue(pattern_matches("*", ""))


class DefaultTierTests(unittest.TestCase):
    def test_default_read_allows(self):
        gate = AuthorizationGate()
        self.assertEqual(gate.decide("Read(file)"), Decision.ALLOW)

    def test_default_write_asks(self):
        gate = AuthorizationGate()
        self.assertEqual(gate.decide("Write(file)", RiskTier.WRITE), Decision.ASK)

    def test_default_irreversible_asks_and_never_allows(self):
        gate = AuthorizationGate()
        self.assertEqual(gate.decide("Drop(db)", RiskTier.IRREVERSIBLE), Decision.ASK)
        self.assertNotEqual(gate.decide("Drop(db)", RiskTier.IRREVERSIBLE), Decision.ALLOW)


class RulePrecedenceTests(unittest.TestCase):
    def test_explicit_deny_wins_over_explicit_allow(self):
        gate = AuthorizationGate()
        gate.add_rule(Rule("Bash(git push *)", Decision.ALLOW))
        gate.add_rule(Rule("Bash(git push *)", Decision.DENY))
        self.assertEqual(gate.decide("Bash(git push origin main)", RiskTier.WRITE), Decision.DENY)

    def test_ask_beats_allow(self):
        gate = AuthorizationGate()
        gate.add_rule(Rule("Bash(npm:*)", Decision.ALLOW, priority=100))
        gate.add_rule(Rule("Bash(npm:*)", Decision.ASK))
        self.assertEqual(gate.decide("Bash(npm:install)", RiskTier.WRITE), Decision.ASK)

    def test_deny_beats_ask_regardless_of_priority(self):
        gate = AuthorizationGate()
        gate.add_rule(Rule("*", Decision.ASK, priority=999))
        gate.add_rule(Rule("Bash(rm *)", Decision.DENY, priority=-5))
        self.assertEqual(gate.decide("Bash(rm -rf /)", RiskTier.IRREVERSIBLE), Decision.DENY)

    def test_priority_breaks_ties_within_same_decision(self):
        gate = AuthorizationGate()
        gate.add_rule(Rule("Bash(git *)", Decision.DENY, priority=1, source="low"))
        gate.add_rule(Rule("Bash(git *)", Decision.DENY, priority=7, source="high"))
        selected = gate._select("Bash(git status)", RiskTier.READ)
        self.assertIsNotNone(selected)
        self.assertEqual(selected.source, "high")

    def test_longer_pattern_wins_at_equal_priority(self):
        gate = AuthorizationGate()
        gate.add_rule(Rule("Bash(*)", Decision.DENY, priority=3, source="broad"))
        gate.add_rule(Rule("Bash(git *)", Decision.DENY, priority=3, source="narrow"))
        selected = gate._select("Bash(git status)", RiskTier.READ)
        self.assertIsNotNone(selected)
        self.assertEqual(selected.source, "narrow")

    def test_insertion_order_breaks_remaining_ties(self):
        gate = AuthorizationGate()
        gate.add_rule(Rule("Bash(x)", Decision.DENY, priority=0, source="first"))
        gate.add_rule(Rule("Bash(x)", Decision.DENY, priority=0, source="second"))
        selected = gate._select("Bash(x)", RiskTier.WRITE)
        self.assertIsNotNone(selected)
        self.assertEqual(selected.source, "first")


class TierScopeTests(unittest.TestCase):
    def test_tier_scoped_rule_only_matches_its_tier(self):
        gate = AuthorizationGate()
        gate.add_rule(Rule("Deploy(*)", Decision.DENY, tier=RiskTier.IRREVERSIBLE))
        self.assertEqual(gate.decide("Deploy(prod)", RiskTier.IRREVERSIBLE), Decision.DENY)
        self.assertEqual(gate.decide("Deploy(prod)", RiskTier.WRITE), Decision.ASK)
        self.assertEqual(gate.decide("Deploy(prod)", RiskTier.READ), Decision.ALLOW)

    def test_tierless_rule_matches_every_tier(self):
        gate = AuthorizationGate()
        gate.add_rule(Rule("Audit(*)", Decision.DENY))
        self.assertEqual(gate.decide("Audit(x)", RiskTier.READ), Decision.DENY)
        self.assertEqual(gate.decide("Audit(x)", RiskTier.WRITE), Decision.DENY)
        self.assertEqual(gate.decide("Audit(x)", RiskTier.IRREVERSIBLE), Decision.DENY)


class StickyDenyTests(unittest.TestCase):
    def test_sticky_deny_survives_later_allow_rules(self):
        gate = AuthorizationGate()
        gate.record_ask_resolution("job-1", Decision.DENY)
        self.assertTrue(gate.is_sticky_denied("job-1"))
        gate.add_rule(Rule("*", Decision.ALLOW, priority=1000))
        self.assertEqual(gate.decide("Bash(anything)", RiskTier.READ, action_id="job-1"), Decision.DENY)

    def test_rule_deny_makes_action_id_sticky(self):
        gate = AuthorizationGate()
        gate.add_rule(Rule("Bash(rm *)", Decision.DENY))
        self.assertEqual(gate.decide("Bash(rm x)", RiskTier.IRREVERSIBLE, action_id="cleanup"), Decision.DENY)
        self.assertTrue(gate.is_sticky_denied("cleanup"))

    def test_ask_resolution_to_allow_is_not_sticky(self):
        gate = AuthorizationGate()
        gate.record_ask_resolution("job-2", Decision.ALLOW)
        self.assertFalse(gate.is_sticky_denied("job-2"))
        self.assertEqual(gate.decide("Write(file)", RiskTier.WRITE, action_id="job-2"), Decision.ASK)

    def test_ask_resolution_to_deny_is_sticky(self):
        gate = AuthorizationGate()
        gate.record_ask_resolution("job-3", Decision.DENY)
        self.assertTrue(gate.is_sticky_denied("job-3"))
        self.assertEqual(gate.decide("Read(file)", RiskTier.READ, action_id="job-3"), Decision.DENY)

    def test_sticky_deny_is_scoped_to_action_id(self):
        gate = AuthorizationGate()
        gate.record_ask_resolution("job-a", Decision.DENY)
        self.assertFalse(gate.is_sticky_denied("job-b"))
        self.assertEqual(gate.decide("Read(file)", RiskTier.READ, action_id="job-b"), Decision.ALLOW)


class AskResolutionTests(unittest.TestCase):
    def test_record_ask_resolution_with_ask_raises(self):
        gate = AuthorizationGate()
        with self.assertRaises(ValueError):
            gate.record_ask_resolution("job-4", Decision.ASK)

    def test_record_ask_resolution_rejects_non_decision(self):
        gate = AuthorizationGate()
        with self.assertRaises(ValueError):
            gate.record_ask_resolution("job-4", "allow")  # type: ignore[arg-type]


class NoAutoEscalationTests(unittest.TestCase):
    def test_no_rule_ever_auto_escalates_ask_to_allow(self):
        gate = AuthorizationGate()
        gate.add_rule(Rule("Write(*)", Decision.ASK))
        gate.add_rule(Rule("Read(*)", Decision.ALLOW))
        self.assertEqual(gate.decide("Write(file)", RiskTier.WRITE), Decision.ASK)
        self.assertEqual(gate.decide("Drop(db)", RiskTier.IRREVERSIBLE), Decision.ASK)

    def test_irreversible_default_never_auto_allows(self):
        gate = AuthorizationGate()
        for action in ("x", "y", "z"):
            self.assertNotEqual(gate.decide(action, RiskTier.IRREVERSIBLE), Decision.ALLOW)


class HistoryTests(unittest.TestCase):
    def test_history_is_append_only_and_ordered(self):
        gate = AuthorizationGate()
        gate.decide("Read(a)", RiskTier.READ, action_id="h1")
        gate.decide("Write(b)", RiskTier.WRITE, action_id="h2")
        gate.decide("Drop(c)", RiskTier.IRREVERSIBLE, action_id="h3")
        self.assertEqual(
            gate.history(),
            [
                ("Read(a)", "h1", Decision.ALLOW),
                ("Write(b)", "h2", Decision.ASK),
                ("Drop(c)", "h3", Decision.ASK),
            ],
        )
        gate.decide("Read(d)", RiskTier.READ)
        self.assertEqual(len(gate.history()), 4)
        self.assertEqual(gate.history()[3][:2], ("Read(d)", ""))

    def test_history_returns_copy(self):
        gate = AuthorizationGate()
        gate.decide("Read(a)")
        snapshot = gate.history()
        snapshot.append(("tamper", "", Decision.DENY))
        self.assertEqual(len(gate.history()), 1)


if __name__ == "__main__":
    unittest.main()
