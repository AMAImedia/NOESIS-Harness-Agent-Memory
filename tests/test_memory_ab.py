import unittest

from noesis_harness.context_engine import ContextItem
from noesis_harness.memory_ab import ControlledMemoryEvaluator, MemoryABCase


class ControlledMemoryTests(unittest.TestCase):
    def test_nextgen_priority_and_provenance_can_improve_recall_at_same_budget(self):
        case = MemoryABCase(
            case_id="case-1",
            query="rollback",
            relevant_source_ids=("verified-rollback",),
            budget_tokens=12,
            legacy_items=(
                ContextItem("noise", "n" * 32, priority=0.1, source_ids=("noise",)),
                ContextItem("target", "verified rollback state", priority=0.2, source_ids=("verified-rollback",)),
            ),
            nextgen_items=(
                ContextItem("target", "verified rollback state", priority=10.0, source_ids=("verified-rollback",), required=True),
                ContextItem("noise", "n" * 32, priority=0.1, source_ids=("noise",)),
            ),
        )
        outcome = ControlledMemoryEvaluator().evaluate_case(case)
        self.assertEqual(outcome.budget_tokens, 12)
        self.assertTrue(outcome.hard_cap_respected)
        self.assertEqual(outcome.legacy_recall, 0.0)
        self.assertEqual(outcome.nextgen_recall, 1.0)
        self.assertEqual(outcome.transfer_gain, 1.0)

    def test_negative_transfer_is_visible_not_hidden(self):
        case = MemoryABCase(
            case_id="case-2",
            query="cache",
            relevant_source_ids=("fresh",),
            budget_tokens=8,
            legacy_items=(ContextItem("fresh", "fresh evidence", priority=1.0, source_ids=("fresh",)),),
            nextgen_items=(ContextItem("stale", "stale evidence", priority=10.0, source_ids=("stale",)),),
        )
        outcome = ControlledMemoryEvaluator().evaluate_case(case)
        self.assertEqual(outcome.legacy_recall, 1.0)
        self.assertEqual(outcome.nextgen_recall, 0.0)
        self.assertEqual(outcome.transfer_gain, -1.0)

    def test_dropped_ids_and_budget_are_recorded(self):
        case = MemoryABCase(
            case_id="case-3",
            query="x",
            relevant_source_ids=(),
            budget_tokens=4,
            legacy_items=(ContextItem("a", "a" * 8, source_ids=("a",)),),
            nextgen_items=(
                ContextItem("required", "ok", required=True, source_ids=("required",)),
                ContextItem("too-large", "x" * 100, priority=1.0, source_ids=("large",)),
            ),
        )
        outcome = ControlledMemoryEvaluator().evaluate_case(case)
        self.assertTrue(outcome.hard_cap_respected)
        self.assertIn("too-large", outcome.nextgen_dropped_ids)
        self.assertLessEqual(outcome.nextgen_used_tokens, outcome.budget_tokens)


if __name__ == "__main__":
    unittest.main()
