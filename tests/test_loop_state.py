"""Tests for noesis_harness.loop_state."""

from __future__ import annotations

import os
import tempfile
import unittest

from noesis_harness.loop_state import (
    LoopState,
    LoopStateError,
    LoopStateStore,
    Understanding,
)


class TestLoopState(unittest.TestCase):

    def test_set_spec(self):
        state = LoopState("growth")
        state.set_spec("Raise signups without changing pricing.")
        self.assertEqual(state.spec, "Raise signups without changing pricing.")

    def test_set_baseline_and_overwrite(self):
        state = LoopState("growth")
        state.set_baseline("signups", 10.0)
        self.assertEqual(state.understanding.baselines["signups"], 10.0)
        state.set_baseline("signups", 11.5)
        self.assertEqual(state.understanding.baselines["signups"], 11.5)
        self.assertEqual(len(state.understanding.baselines), 1)

    def test_baseline_rejects_non_numeric(self):
        state = LoopState("growth")
        with self.assertRaises(LoopStateError):
            state.set_baseline("signups", "lots")

    def test_add_non_problem_dedupes(self):
        state = LoopState("growth")
        self.assertTrue(state.add_non_problem("onboarding page loads fast"))
        self.assertFalse(state.add_non_problem("onboarding page loads fast"))
        self.assertEqual(
            state.understanding.verified_non_problems,
            ["onboarding page loads fast"],
        )

    def test_add_ruled_out_dedupes(self):
        state = LoopState("growth")
        self.assertTrue(state.add_ruled_out("paid ads"))
        self.assertFalse(state.add_ruled_out("paid ads"))

    def test_record_change_dedupes(self):
        state = LoopState("growth")
        self.assertTrue(state.record_change("shortened hero copy"))
        self.assertFalse(state.record_change("shortened hero copy"))

    def test_add_gotcha_dedupes(self):
        state = LoopState("growth")
        self.assertTrue(state.add_gotcha("staging DB resets nightly"))
        self.assertFalse(state.add_gotcha("staging DB resets nightly"))

    def test_list_adds_are_sorted_deterministically(self):
        state = LoopState("growth")
        state.add_ruled_out("zeta")
        state.add_ruled_out("alpha")
        state.add_ruled_out("mu")
        self.assertEqual(state.understanding.ruled_out, ["alpha", "mu", "zeta"])

    def test_empty_entry_rejected(self):
        state = LoopState("growth")
        with self.assertRaises(LoopStateError):
            state.add_gotcha("   ")

    def test_timeline_append_order_and_format(self):
        state = LoopState("growth")
        first = state.append_timeline("2026-01-01", "run", "checked baselines")
        second = state.append_timeline("2026-01-02", "run", "shipped hero")
        self.assertEqual(first, "2026-01-01 | run \u2014 checked baselines")
        self.assertEqual(second, "2026-01-02 | run \u2014 shipped hero")
        self.assertEqual(
            state.timeline(),
            [
                "2026-01-01 | run \u2014 checked baselines",
                "2026-01-02 | run \u2014 shipped hero",
            ],
        )

    def test_timeline_returns_copy_and_is_append_only(self):
        state = LoopState("growth")
        state.append_timeline("2026-01-01", "run", "same")
        state.append_timeline("2026-01-01", "run", "same")
        self.assertEqual(len(state.timeline()), 2)
        snapshot = state.timeline()
        snapshot.append("tampered")
        self.assertEqual(len(state.timeline()), 2)

    def test_frequency_equals_timeline_length(self):
        state = LoopState("growth")
        self.assertIn("frequency: 0", state.render())
        state.append_timeline("2026-01-01", "run", "one")
        state.append_timeline("2026-01-02", "run", "two")
        self.assertIn("frequency: 2", state.render())

    def test_render_contains_all_sections(self):
        state = LoopState("growth", spec="Grow signups.")
        state.set_baseline("signups", 10.0)
        state.add_non_problem("onboarding is fine")
        state.add_ruled_out("paid ads")
        state.record_change("shortened hero")
        state.add_gotcha("staging resets nightly")
        state.append_timeline("2026-01-01", "run", "started")
        text = state.render()
        for marker in (
            "kind: loop-state",
            "name: growth",
            "## Spec",
            "## Current understanding",
            "### Baselines",
            "### Verified non-problems",
            "### Ruled out",
            "### Applied changes",
            "### Gotchas",
            "## Timeline",
        ):
            self.assertIn(marker, text)

    def test_render_deterministic(self):
        state = LoopState("growth", spec="Grow signups.")
        state.set_baseline("b", 2.0)
        state.set_baseline("a", 1.0)
        state.add_ruled_out("z")
        state.add_ruled_out("a")
        state.append_timeline("2026-01-01", "run", "one")
        self.assertEqual(state.render(), state.render())

    def test_render_sorts_baseline_keys(self):
        state = LoopState("growth")
        state.set_baseline("zeta", 1.0)
        state.set_baseline("alpha", 2.0)
        text = state.render()
        self.assertLess(text.index("- alpha:"), text.index("- zeta:"))

    def test_empty_state_renders_validly(self):
        state = LoopState("empty")
        text = state.render()
        self.assertIn("kind: loop-state", text)
        self.assertIn("frequency: 0", text)
        self.assertIn("## Spec", text)
        self.assertIn("## Timeline", text)

    def test_parse_roundtrip_preserves_fields(self):
        state = LoopState("growth loop", spec="Grow signups.")
        state.set_baseline("signups", 10.5)
        state.set_baseline("churn", 0.25)
        state.add_non_problem("onboarding is fine")
        state.add_ruled_out("paid ads")
        state.record_change("shortened hero")
        state.add_gotcha("staging resets nightly")
        state.append_timeline("2026-01-01", "run", "started")
        state.append_timeline("2026-01-02", "run", "shipped")

        parsed = LoopState.parse(state.render())

        self.assertEqual(parsed.name, "growth loop")
        self.assertEqual(parsed.spec, "Grow signups.")
        self.assertEqual(parsed.understanding.baselines, {"signups": 10.5, "churn": 0.25})
        self.assertEqual(
            parsed.understanding.verified_non_problems, ["onboarding is fine"]
        )
        self.assertEqual(parsed.understanding.ruled_out, ["paid ads"])
        self.assertEqual(parsed.understanding.applied_changes, ["shortened hero"])
        self.assertEqual(parsed.understanding.gotchas, ["staging resets nightly"])
        self.assertEqual(parsed.timeline(), state.timeline())
        self.assertEqual(parsed.render(), state.render())

    def test_parse_empty_state(self):
        parsed = LoopState.parse(LoopState("empty").render())
        self.assertEqual(parsed.name, "empty")
        self.assertEqual(parsed.spec, "")
        self.assertEqual(parsed.timeline(), [])

    def test_digest_stable_and_changes(self):
        state = LoopState("growth")
        first = state.digest()
        self.assertTrue(first.startswith("sha256:"))
        self.assertEqual(first, state.digest())
        state.record_change("shortened hero")
        self.assertNotEqual(first, state.digest())

    def test_name_validation(self):
        with self.assertRaises(LoopStateError):
            LoopState("")
        with self.assertRaises(LoopStateError):
            LoopState("   ")
        with self.assertRaises(LoopStateError):
            LoopState(None)

    def test_understanding_defaults(self):
        understanding = Understanding()
        self.assertEqual(understanding.baselines, {})
        self.assertEqual(understanding.verified_non_problems, [])
        self.assertEqual(understanding.ruled_out, [])
        self.assertEqual(understanding.applied_changes, [])
        self.assertEqual(understanding.gotchas, [])

    def test_loop_state_error_is_runtime_error(self):
        self.assertTrue(issubclass(LoopStateError, RuntimeError))


class TestLoopStateStore(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store = LoopStateStore(self._tmp.name)

    def _make(self, name):
        state = LoopState(name, spec="do the thing")
        state.record_change("did the thing")
        state.append_timeline("2026-01-01", "run", "started")
        return state

    def test_save_load_roundtrip(self):
        state = self._make("alpha")
        path = self.store.save(state)
        self.assertTrue(os.path.exists(path))
        loaded = self.store.load("alpha")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.render(), state.render())

    def test_save_returns_path_with_safe_filename(self):
        state = LoopState("my loop/v1")
        path = self.store.save(state)
        self.assertEqual(path, os.path.join(self._tmp.name, "my_loop_v1.md"))

    def test_names_sorted(self):
        for name in ("zeta", "alpha", "mid"):
            self.store.save(self._make(name))
        self.assertEqual(self.store.names(), ["alpha", "mid", "zeta"])

    def test_load_unknown_returns_none(self):
        self.assertIsNone(self.store.load("does-not-exist"))

    def test_names_missing_directory_is_empty(self):
        store = LoopStateStore(os.path.join(self._tmp.name, "absent"))
        self.assertEqual(store.names(), [])

    def test_save_creates_missing_root(self):
        nested = os.path.join(self._tmp.name, "a", "b")
        store = LoopStateStore(nested)
        path = store.save(self._make("deep"))
        self.assertTrue(os.path.exists(path))

    def test_load_rejects_wrong_type_state(self):
        with self.assertRaises(LoopStateError):
            self.store.save("not a state")


if __name__ == "__main__":
    unittest.main()
