"""Tests for noesis_harness.loop_contract.

The loop-contract helpers are pure and deterministic; these tests pin the
validation rules, gate evaluation (including fail-closed behaviour), the
hand-rolled frontmatter round trip, and registry semantics.
"""

import unittest

from noesis_harness.loop_contract import (
    Cadence,
    GateCondition,
    LoopContract,
    LoopRegistry,
    LoopStatus,
    kebab_case,
)


def _valid_contract(**overrides):
    payload = {
        "name": "alpha-loop",
        "goal": "Ship the alpha milestone",
        "produces": ["report.md"],
    }
    payload.update(overrides)
    return LoopContract(**payload)


class TestKebabCase(unittest.TestCase):
    def test_spaces_and_case_fold(self):
        self.assertEqual(kebab_case("My Loop Name"), "my-loop-name")

    def test_camel_case_split(self):
        self.assertEqual(kebab_case("MyLoop"), "my-loop")

    def test_existing_separators_collapse(self):
        self.assertEqual(kebab_case("already_kebab"), "already-kebab")
        self.assertEqual(kebab_case("  Trim Me  "), "trim-me")

    def test_empty(self):
        self.assertEqual(kebab_case(""), "")


class TestValidation(unittest.TestCase):
    def test_empty_goal_is_reported(self):
        problems = _valid_contract(goal="").validate()
        self.assertTrue(any("goal" in item for item in problems))

    def test_bad_name_not_kebab_is_reported(self):
        problems = _valid_contract(name="Bad Name").validate()
        self.assertTrue(any("kebab" in item for item in problems))

    def test_empty_produces_is_reported(self):
        problems = _valid_contract(produces=[]).validate()
        self.assertTrue(any("produces" in item for item in problems))

    def test_valid_contract_has_no_problems(self):
        self.assertEqual(_valid_contract().validate(), [])


class TestBacklog(unittest.TestCase):
    def test_add_and_next_backlog_is_fifo(self):
        contract = _valid_contract()
        contract.add_backlog("first")
        contract.add_backlog("second")
        self.assertEqual(contract.next_backlog(), "first")
        self.assertEqual(contract.backlog, ["first", "second"])

    def test_next_backlog_empty_returns_none(self):
        self.assertIsNone(_valid_contract().next_backlog())


class TestGateCondition(unittest.TestCase):
    def test_evaluate_various_operators(self):
        self.assertTrue(
            GateCondition("score", ">=", 0.5, Cadence.WEEKLY).evaluate({"score": 0.5})
        )
        self.assertFalse(
            GateCondition("score", ">=", 0.5, Cadence.WEEKLY).evaluate({"score": 0.49})
        )
        self.assertTrue(
            GateCondition("errors", "==", 0.0, Cadence.DAILY).evaluate({"errors": 0})
        )
        self.assertFalse(
            GateCondition("errors", "<", 1.0, Cadence.DAILY).evaluate({"errors": 1.0})
        )

    def test_missing_metric_is_fail_closed(self):
        gate = GateCondition("score", ">=", 0.0, Cadence.WEEKLY)
        self.assertFalse(gate.evaluate({}))
        self.assertFalse(gate.evaluate({"other": 1.0}))

    def test_non_numeric_metric_is_fail_closed(self):
        gate = GateCondition("score", ">=", 0.0, Cadence.WEEKLY)
        self.assertFalse(gate.evaluate({"score": "not-a-number"}))

    def test_invalid_operator_raises(self):
        with self.assertRaises(ValueError):
            GateCondition("score", "!=", 1.0, Cadence.DAILY)

    def test_cadence_and_threshold_are_coerced(self):
        gate = GateCondition("score", ">=", 55, "weekly")
        self.assertEqual(gate.target_cadence, Cadence.WEEKLY)
        self.assertIsInstance(gate.threshold, float)


class TestEffectiveCadence(unittest.TestCase):
    def test_base_cadence_when_no_gate(self):
        contract = _valid_contract(cadence=Cadence.DAILY)
        self.assertEqual(contract.effective_cadence({"score": 999.0}), Cadence.DAILY)

    def test_base_cadence_when_no_gate_satisfied(self):
        contract = _valid_contract(
            cadence=Cadence.DAILY,
            gates=[GateCondition("score", ">=", 0.9, Cadence.WEEKLY)],
        )
        self.assertEqual(contract.effective_cadence({"score": 0.1}), Cadence.DAILY)

    def test_first_satisfied_gate_wins(self):
        contract = _valid_contract(
            cadence=Cadence.MANUAL,
            gates=[
                GateCondition("score", ">=", 0.5, Cadence.WEEKLY),
                GateCondition("latency", "<", 100.0, Cadence.CRON),
            ],
        )
        values = {"score": 0.8, "latency": 10.0}
        self.assertEqual(contract.effective_cadence(values), Cadence.WEEKLY)

    def test_later_gate_wins_when_first_not_satisfied(self):
        contract = _valid_contract(
            cadence=Cadence.MANUAL,
            gates=[
                GateCondition("score", ">=", 0.9, Cadence.WEEKLY),
                GateCondition("latency", "<", 100.0, Cadence.CRON),
            ],
        )
        values = {"score": 0.1, "latency": 10.0}
        self.assertEqual(contract.effective_cadence(values), Cadence.CRON)


class TestFrontmatter(unittest.TestCase):
    def test_roundtrip_preserves_fields(self):
        contract = LoopContract(
            name="alpha-loop",
            goal="Ship the alpha milestone",
            cadence=Cadence.WEEKLY,
            status=LoopStatus.PAUSED,
            consumes=["spec.md", "docs"],
            produces=["report.md"],
            backlog=["first item", "second item"],
            current_focus="Tighten the parser",
            gates=[
                GateCondition("chrf", ">=", 55.0, Cadence.WEEKLY),
                GateCondition("cer", "<", 0.1, Cadence.DAILY),
            ],
        )
        parsed = LoopContract.from_frontmatter(contract.to_frontmatter())
        self.assertEqual(parsed, contract)

    def test_rendered_document_has_expected_sections_and_header(self):
        text = _valid_contract().to_frontmatter()
        self.assertIn("kind: domain", text)
        self.assertIn("## Current focus", text)
        self.assertIn("## Backlog", text)
        self.assertIn("## Evidence & analysis", text)
        self.assertIn("## Metrics", text)
        self.assertIn("## Timeline", text)

    def test_from_frontmatter_is_tolerant_of_missing_optionals(self):
        text = "---\nkind: domain\ndomain: solo-loop\n---\n"
        contract = LoopContract.from_frontmatter(text)
        self.assertEqual(contract.name, "solo-loop")
        self.assertEqual(contract.goal, "")
        self.assertEqual(contract.cadence, Cadence.MANUAL)
        self.assertEqual(contract.status, LoopStatus.ACTIVE)
        self.assertEqual(contract.consumes, [])
        self.assertEqual(contract.produces, [])
        self.assertEqual(contract.backlog, [])
        self.assertEqual(contract.current_focus, "")
        self.assertEqual(contract.gates, [])

    def test_from_frontmatter_accepts_name_key_as_fallback(self):
        text = "---\nname: legacy-loop\ngoal: Go\nproduces: [a.md]\n---\n"
        contract = LoopContract.from_frontmatter(text)
        self.assertEqual(contract.name, "legacy-loop")
        self.assertEqual(contract.produces, ["a.md"])


class TestCoercion(unittest.TestCase):
    def test_status_and_cadence_coerced_from_string(self):
        contract = LoopContract(name="x-loop", goal="go", cadence="DAILY", status="Paused")
        self.assertEqual(contract.cadence, Cadence.DAILY)
        self.assertEqual(contract.status, LoopStatus.PAUSED)

    def test_invalid_status_raises(self):
        with self.assertRaises(ValueError):
            LoopContract(name="x-loop", goal="go", status="sleeping")


class TestLoopRegistry(unittest.TestCase):
    def test_register_and_duplicate_raises(self):
        registry = LoopRegistry()
        registry.register(_valid_contract(name="a-loop"))
        with self.assertRaises(ValueError):
            registry.register(_valid_contract(name="a-loop"))

    def test_names_are_sorted(self):
        registry = LoopRegistry()
        registry.register(_valid_contract(name="c-loop"))
        registry.register(_valid_contract(name="a-loop"))
        registry.register(_valid_contract(name="b-loop"))
        self.assertEqual(registry.names(), ["a-loop", "b-loop", "c-loop"])

    def test_active_filters_archived_and_paused(self):
        registry = LoopRegistry()
        registry.register(_valid_contract(name="live-loop"))
        registry.register(
            _valid_contract(name="done-loop", status=LoopStatus.ARCHIVED)
        )
        registry.register(_valid_contract(name="held-loop", status=LoopStatus.PAUSED))
        self.assertEqual([c.name for c in registry.active()], ["live-loop"])

    def test_get_returns_contract_or_none(self):
        registry = LoopRegistry()
        contract = _valid_contract(name="a-loop")
        registry.register(contract)
        self.assertIs(registry.get("a-loop"), contract)
        self.assertIsNone(registry.get("missing-loop"))

    def test_by_cadence_returns_sorted_names(self):
        registry = LoopRegistry()
        registry.register(_valid_contract(name="b-loop", cadence=Cadence.DAILY))
        registry.register(_valid_contract(name="a-loop", cadence=Cadence.DAILY))
        registry.register(_valid_contract(name="c-loop", cadence=Cadence.WEEKLY))
        self.assertEqual(registry.by_cadence(Cadence.DAILY), ["a-loop", "b-loop"])
        self.assertEqual(registry.by_cadence("weekly"), ["c-loop"])


class TestDeterminism(unittest.TestCase):
    def test_repeated_calls_are_stable(self):
        contract = LoopContract(
            name="alpha-loop",
            goal="Ship it",
            cadence=Cadence.DAILY,
            produces=["report.md"],
            backlog=["one", "two"],
            gates=[GateCondition("score", ">=", 0.5, Cadence.WEEKLY)],
        )
        self.assertEqual(contract.to_frontmatter(), contract.to_frontmatter())
        values = {"score": 0.9}
        self.assertEqual(
            contract.effective_cadence(values), contract.effective_cadence(values)
        )
        registry = LoopRegistry()
        registry.register(contract)
        self.assertEqual(registry.names(), registry.names())


if __name__ == "__main__":
    unittest.main()
