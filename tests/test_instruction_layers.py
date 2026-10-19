"""tests/test_instruction_layers.py

Unit tests for noesis_harness.instruction_layers.

Stdlib only. Run: python -m unittest tests.test_instruction_layers -q
"""

import unittest
from types import SimpleNamespace

from noesis_harness.instruction_layers import (
    PRECEDENCE,
    InstructionFragment,
    InstructionStack,
    LayerSource,
    assert_no_replacement,
)


class TestInstructionLayers(unittest.TestCase):
    def test_precedence_table_is_ordered(self):
        self.assertEqual(PRECEDENCE[LayerSource.MANAGED], 10)
        self.assertEqual(PRECEDENCE[LayerSource.USER], 20)
        self.assertEqual(PRECEDENCE[LayerSource.PROJECT], 30)
        self.assertEqual(PRECEDENCE[LayerSource.LOCAL], 40)
        self.assertEqual(PRECEDENCE[LayerSource.RUNTIME], 50)

    def test_resolve_orders_by_authority(self):
        stack = InstructionStack()
        stack.add(InstructionFragment(source=LayerSource.RUNTIME, text="runtime rule"))
        stack.add(InstructionFragment(source=LayerSource.MANAGED, text="managed rule"))
        resolved = stack.resolve()
        self.assertLess(resolved.index("managed rule"), resolved.index("runtime rule"))

    def test_higher_source_after_lower(self):
        stack = InstructionStack()
        stack.add(InstructionFragment(source=LayerSource.PROJECT, text="project"))
        stack.add(InstructionFragment(source=LayerSource.USER, text="user"))
        ordered = [f.source for f in stack.fragments()]
        self.assertEqual(ordered, [LayerSource.USER, LayerSource.PROJECT])

    def test_precedence_offset_reorders_within_source(self):
        stack = InstructionStack()
        base = InstructionFragment(source=LayerSource.PROJECT, text="base")
        early = InstructionFragment(source=LayerSource.PROJECT, text="early", precedence=-5)
        stack.add(base)
        stack.add(early)
        texts = [f.text for f in stack.fragments()]
        self.assertEqual(texts, ["early", "base"])

    def test_append_only_rendered_after_base(self):
        stack = InstructionStack()
        stack.add(InstructionFragment(source=LayerSource.PROJECT, text="base text"))
        stack.append(LayerSource.PROJECT, "appended text")
        resolved = stack.resolve()
        self.assertLess(resolved.index("base text"), resolved.index("appended text"))

    def test_base_survives_an_append(self):
        stack = InstructionStack()
        stack.add(InstructionFragment(source=LayerSource.PROJECT, text="must survive"))
        before = stack.resolve()
        stack.append(LayerSource.PROJECT, "extra")
        after = stack.resolve()
        self.assertIn("must survive", after)
        self.assertTrue(assert_no_replacement(before, after))

    def test_append_only_cannot_jump_before_base(self):
        stack = InstructionStack()
        stack.add(InstructionFragment(source=LayerSource.PROJECT, text="base"))
        stack.append(LayerSource.PROJECT, "append with low precedence", precedence=-100)
        texts = [f.text for f in stack.fragments()]
        self.assertEqual(texts, ["base", "append with low precedence"])

    def test_empty_text_raises_on_fragment(self):
        with self.assertRaises(ValueError):
            InstructionFragment(source=LayerSource.USER, text="   ")

    def test_add_raises_on_empty_text(self):
        caught = False
        stack = InstructionStack()
        fake = SimpleNamespace(
            source=LayerSource.USER,
            text="   ",
            precedence=0,
            append_only=False,
        )
        try:
            stack.add(fake)
        except ValueError:
            caught = True
        self.assertTrue(caught)

    def test_source_separators_on_change_only(self):
        stack = InstructionStack()
        stack.add(InstructionFragment(source=LayerSource.MANAGED, text="m1"))
        stack.add(InstructionFragment(source=LayerSource.MANAGED, text="m2"))
        stack.add(InstructionFragment(source=LayerSource.PROJECT, text="p1"))
        resolved = stack.resolve()
        self.assertEqual(resolved.count("# managed"), 1)
        self.assertEqual(resolved.count("# project"), 1)
        self.assertIn("# managed\nm1", resolved)
        self.assertIn("# project\np1", resolved)

    def test_base_for_returns_first_non_append(self):
        stack = InstructionStack()
        stack.add(InstructionFragment(source=LayerSource.USER, text="base user"))
        stack.append(LayerSource.USER, "extra user")
        self.assertEqual(stack.base_for(LayerSource.USER), "base user")
        self.assertIsNone(stack.base_for(LayerSource.RUNTIME))

    def test_base_for_skips_append_only(self):
        stack = InstructionStack()
        stack.append(LayerSource.LOCAL, "only append")
        self.assertIsNone(stack.base_for(LayerSource.LOCAL))

    def test_fragments_in_resolution_order(self):
        stack = InstructionStack()
        stack.add(InstructionFragment(source=LayerSource.RUNTIME, text="r"))
        stack.add(InstructionFragment(source=LayerSource.MANAGED, text="m"))
        stack.add(InstructionFragment(source=LayerSource.USER, text="u"))
        sources = [f.source for f in stack.fragments()]
        self.assertEqual(
            sources,
            [LayerSource.MANAGED, LayerSource.USER, LayerSource.RUNTIME],
        )

    def test_sources_sorted_by_authority(self):
        stack = InstructionStack()
        stack.add(InstructionFragment(source=LayerSource.RUNTIME, text="r"))
        stack.add(InstructionFragment(source=LayerSource.MANAGED, text="m"))
        stack.add(InstructionFragment(source=LayerSource.MANAGED, text="m2"))
        self.assertEqual(stack.sources(), [LayerSource.MANAGED, LayerSource.RUNTIME])

    def test_digest_stability_and_change(self):
        stack = InstructionStack()
        stack.add(InstructionFragment(source=LayerSource.USER, text="hello"))
        first = stack.digest()
        self.assertTrue(first.startswith("sha256:"))
        self.assertEqual(first, stack.digest())
        stack.append(LayerSource.USER, "world")
        self.assertNotEqual(first, stack.digest())

    def test_digest_matches_resolved_text(self):
        import hashlib

        stack = InstructionStack()
        stack.add(InstructionFragment(source=LayerSource.LOCAL, text="local rule"))
        expected = "sha256:" + hashlib.sha256(stack.resolve().encode("utf-8")).hexdigest()
        self.assertEqual(stack.digest(), expected)

    def test_append_helper_sets_append_only(self):
        stack = InstructionStack()
        fragment = stack.append(LayerSource.RUNTIME, "runtime extra", precedence=3)
        self.assertTrue(fragment.append_only)
        self.assertEqual(fragment.source, LayerSource.RUNTIME)
        self.assertEqual(fragment.precedence, 3)

    def test_assert_no_replacement_true_and_false(self):
        before = "# managed\nrule one\n\n# project\nrule two"
        after = "# managed\nrule one\n\n# project\nrule two\nrule three"
        self.assertTrue(assert_no_replacement(before, after))
        dropped = "# managed\nrule one\n\n# project"
        self.assertFalse(assert_no_replacement(before, dropped))

    def test_assert_no_replacement_ignores_blank_lines(self):
        self.assertTrue(assert_no_replacement("a\n\n\nb", "a\nb"))

    def test_determinism_across_identical_stacks(self):
        def build():
            stack = InstructionStack()
            stack.add(InstructionFragment(source=LayerSource.PROJECT, text="base"))
            stack.append(LayerSource.PROJECT, "extra")
            stack.add(InstructionFragment(source=LayerSource.USER, text="user"))
            return stack

        first = build()
        second = build()
        self.assertEqual(first.resolve(), second.resolve())
        self.assertEqual(first.digest(), second.digest())


if __name__ == "__main__":
    unittest.main()
