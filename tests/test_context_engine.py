import unittest

from noesis_harness.context_engine import BudgetedContextAssembler, ContextItem


class ContextEngineTests(unittest.TestCase):
    def test_hard_budget_and_provenance(self):
        assembler=BudgetedContextAssembler(12)
        items=[
            ContextItem("policy", "P"*16, priority=100, category="pinned", source_ids=("policy-1",), required=True),
            ContextItem("evidence", "E"*20, priority=10, source_ids=("ev-1",)),
            ContextItem("recent", "R"*20, priority=1, category="recent", source_ids=("msg-1",)),
        ]
        result=assembler.assemble(items)
        self.assertLessEqual(result.used_tokens, 12)
        self.assertEqual(result.selected_ids[0], "policy")
        self.assertIn("policy-1", result.source_ids)
        self.assertTrue(result.dropped_ids)

    def test_duplicate_ids_are_deduplicated_and_empty_is_safe(self):
        assembler=BudgetedContextAssembler(20)
        result=assembler.assemble([ContextItem("x", "hello", 1), ContextItem("x", "other", 2)])
        self.assertEqual(result.selected_ids, ("x",))
        self.assertEqual(assembler.assemble(()).coverage, 1.0)


if __name__ == "__main__": unittest.main()

