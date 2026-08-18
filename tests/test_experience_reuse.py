from __future__ import annotations

import unittest

from noesis_harness.experience_reuse import ExperienceRecord, ExperienceReuseSelector


class ExperienceReuseTests(unittest.TestCase):
    def record(self, experience_id: str, content: str, **kwargs) -> ExperienceRecord:
        return ExperienceRecord(
            experience_id,
            content,
            provenance_digest="sha256:" + "a" * 64,
            success_score=kwargs.pop("success_score", 0.9),
            recency_score=kwargs.pop("recency_score", 0.9),
            **kwargs,
        )

    def test_scope_and_sensitivity_are_deny_by_default(self):
        decision = ExperienceReuseSelector().select(
            [
                self.record("local", "local result"),
                self.record("other-agent", "private result", scope="agent:other"),
                self.record("restricted", "restricted result", sensitivity="restricted"),
            ]
        )
        self.assertEqual([item.experience_id for item in decision.selected], ["local"])
        self.assertIn(("other-agent", "scope_denied"), decision.excluded)
        self.assertIn(("restricted", "sensitivity_denied"), decision.excluded)

    def test_deterministic_score_order_and_digest(self):
        records = [
            self.record("b", "B", success_score=0.8, recency_score=0.8),
            self.record("a", "A", success_score=0.8, recency_score=0.8),
        ]
        first = ExperienceReuseSelector(max_chars=10).select(records)
        second = ExperienceReuseSelector(max_chars=10).select(reversed(records))
        self.assertEqual(tuple(item.experience_id for item in first.selected), ("a", "b"))
        self.assertEqual(first.digest, second.digest)

    def test_budgets_are_explicit_and_exclusions_explainable(self):
        decision = ExperienceReuseSelector(max_chars=5, max_items=1).select(
            [self.record("one", "1234"), self.record("two", "5678")]
        )
        self.assertEqual(len(decision.selected), 1)
        self.assertEqual(decision.used_chars, 4)
        self.assertEqual(decision.excluded, (("two", "item_budget"),))

    def test_invalid_provenance_is_not_reused(self):
        invalid = ExperienceRecord("invalid", "data", provenance_digest="missing")
        decision = ExperienceReuseSelector().select([invalid])
        self.assertEqual(decision.selected, ())
        self.assertEqual(decision.excluded, (("invalid", "provenance_digest_required"),))


if __name__ == "__main__":
    unittest.main()
