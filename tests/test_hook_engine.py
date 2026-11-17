"""Tests for noesis_harness.hook_engine.

Covers the HookEvent surface, Hook validation, HookResult flattening,
registration and duplicate rejection, stable (display_order, name) ordering,
the preview/run split (preview never calls callbacks and reflects disabled
state), failure isolation, payload mutation isolation, enable/disable, clear,
last_results, and the enabled-hook budget guard. Stdlib only, deterministic.
"""

import unittest

from noesis_harness.hook_engine import (
    Hook,
    HookBudgetError,
    HookEngine,
    HookEvent,
    HookResult,
)


class _Recorder(object):
    """Collects invocation order and can mutate the payload it receives."""

    def __init__(self, label="", output="ok", raises=None, mutate=None):
        self.label = label
        self.output = output
        self.raises = raises
        self.mutate = mutate
        self.calls = []

    def __call__(self, payload):
        self.calls.append(dict(payload))
        if self.mutate is not None:
            self.mutate(payload)
        if self.raises is not None:
            raise self.raises
        return self.output


def _hook(name, event=HookEvent.PRE_TOOL, callback=None, display_order=0,
          enabled=True):
    if callback is None:
        callback = _Recorder()
    return Hook(name=name, event=event, callback=callback,
                display_order=display_order, enabled=enabled)


class TestHookEvent(unittest.TestCase):

    def test_surface_is_complete(self):
        self.assertEqual(
            [e.value for e in HookEvent],
            ["pre_tool", "post_tool", "session_start", "session_end",
             "pre_compact", "subagent_start", "subagent_stop"],
        )

    def test_event_is_str_compatible(self):
        self.assertEqual(HookEvent.PRE_TOOL, "pre_tool")


class TestHookValidation(unittest.TestCase):

    def test_empty_name_rejected(self):
        with self.assertRaises(ValueError):
            _hook("")

    def test_whitespace_name_rejected(self):
        with self.assertRaises(ValueError):
            _hook("   ")

    def test_non_callable_callback_rejected(self):
        with self.assertRaises(ValueError):
            Hook(name="x", event=HookEvent.PRE_TOOL, callback="not-callable")


class TestRegistration(unittest.TestCase):

    def test_register_and_list(self):
        engine = HookEngine()
        engine.register(_hook("a"))
        self.assertEqual([h.name for h in engine.hooks()], ["a"])

    def test_duplicate_name_raises(self):
        engine = HookEngine()
        engine.register(_hook("a"))
        with self.assertRaises(ValueError):
            engine.register(_hook("a"))

    def test_ordering_by_display_order_then_name(self):
        engine = HookEngine()
        engine.register(_hook("zeta", display_order=1))
        engine.register(_hook("alpha", display_order=1))
        engine.register(_hook("first", display_order=0))
        self.assertEqual(
            [h.name for h in engine.hooks()],
            ["first", "alpha", "zeta"],
        )

    def test_hooks_filtered_by_event(self):
        engine = HookEngine()
        engine.register(_hook("pre", event=HookEvent.PRE_TOOL))
        engine.register(_hook("post", event=HookEvent.POST_TOOL))
        self.assertEqual(
            [h.name for h in engine.hooks(HookEvent.POST_TOOL)], ["post"])


class TestPreview(unittest.TestCase):

    def test_preview_does_not_call_callbacks(self):
        engine = HookEngine()
        rec = _Recorder()
        engine.register(_hook("a", callback=rec))
        engine.register(_hook("b", display_order=1))
        items = engine.preview(HookEvent.PRE_TOOL, {"x": 1})
        self.assertEqual(rec.calls, [])
        self.assertEqual([i["name"] for i in items], ["a", "b"])
        self.assertEqual(
            sorted(items[0].keys()), ["display_order", "event", "name"])

    def test_preview_reflects_disabled_state(self):
        engine = HookEngine()
        engine.register(_hook("a"))
        engine.register(_hook("b", display_order=1))
        engine.disable("a")
        self.assertEqual(
            [i["name"] for i in engine.preview(HookEvent.PRE_TOOL)], ["b"])

    def test_preview_empty_for_other_event(self):
        engine = HookEngine()
        engine.register(_hook("a", event=HookEvent.PRE_TOOL))
        self.assertEqual(engine.preview(HookEvent.SESSION_START), [])


class TestFire(unittest.TestCase):

    def test_fire_runs_in_order(self):
        engine = HookEngine()
        order = []
        engine.register(_hook("b", display_order=1,
                              callback=lambda p: order.append("b") or "b"))
        engine.register(_hook("a", display_order=0,
                              callback=lambda p: order.append("a") or "a"))
        results = engine.fire(HookEvent.PRE_TOOL)
        self.assertEqual(order, ["a", "b"])
        self.assertEqual([r.hook for r in results], ["a", "b"])
        self.assertTrue(all(r.ok for r in results))

    def test_exception_is_captured_and_does_not_stop_others(self):
        engine = HookEngine()
        engine.register(_hook("boom", display_order=0,
                              callback=_Recorder(raises=RuntimeError("kaboom"))))
        engine.register(_hook("after", display_order=1))
        results = engine.fire(HookEvent.PRE_TOOL)
        self.assertFalse(results[0].ok)
        self.assertEqual(results[0].output, "kaboom")
        self.assertTrue(results[1].ok)
        self.assertEqual(results[1].hook, "after")

    def test_hook_for_another_event_not_run(self):
        engine = HookEngine()
        other = _Recorder()
        engine.register(_hook("pre", event=HookEvent.PRE_TOOL))
        engine.register(_hook("post", event=HookEvent.POST_TOOL,
                              callback=other))
        engine.fire(HookEvent.PRE_TOOL)
        self.assertEqual(other.calls, [])

    def test_payload_mutation_isolation(self):
        engine = HookEngine()
        engine.register(_hook("mut", display_order=0,
                              callback=_Recorder(mutate=lambda p: p.__setitem__("x", 99))))
        engine.register(_hook("seen", display_order=1))
        seen = []
        engine.register(_hook("record", display_order=2,
                              callback=lambda p: seen.append(dict(p)) or "r"))
        payload = {"x": 1}
        engine.fire(HookEvent.PRE_TOOL, payload)
        self.assertEqual(payload, {"x": 1})
        self.assertEqual(seen, [{"x": 1}])

    def test_payload_none_is_safe(self):
        engine = HookEngine()
        engine.register(_hook("a"))
        self.assertTrue(engine.fire(HookEvent.PRE_TOOL)[0].ok)

    def test_determinism_across_runs(self):
        engine = HookEngine()
        for name, order in (("z", 1), ("a", 1), ("m", 0)):
            engine.register(_hook(name, display_order=order))
        first = [(r.hook, r.ok) for r in engine.fire(HookEvent.PRE_TOOL)]
        second = [(r.hook, r.ok) for r in engine.fire(HookEvent.PRE_TOOL)]
        self.assertEqual(first, second)
        self.assertEqual([n for n, _ in first], ["m", "a", "z"])


class TestToggleAndResults(unittest.TestCase):

    def test_disable_enable(self):
        engine = HookEngine()
        engine.register(_hook("a"))
        self.assertTrue(engine.disable("a"))
        self.assertFalse(engine.hooks()[0].enabled)
        self.assertTrue(engine.enable("a"))
        self.assertTrue(engine.hooks()[0].enabled)

    def test_toggle_unknown_name_returns_false(self):
        engine = HookEngine()
        self.assertFalse(engine.disable("missing"))
        self.assertFalse(engine.enable("missing"))

    def test_disabled_hook_not_fired(self):
        engine = HookEngine()
        rec = _Recorder()
        engine.register(_hook("a", callback=rec))
        engine.disable("a")
        results = engine.fire(HookEvent.PRE_TOOL)
        self.assertEqual(results, [])
        self.assertEqual(rec.calls, [])

    def test_last_results(self):
        engine = HookEngine()
        engine.register(_hook("a"))
        self.assertEqual(engine.last_results(), [])
        engine.fire(HookEvent.PRE_TOOL)
        self.assertEqual([r.hook for r in engine.last_results()], ["a"])

    def test_last_results_returns_copy(self):
        engine = HookEngine()
        engine.register(_hook("a"))
        engine.fire(HookEvent.PRE_TOOL)
        snapshot = engine.last_results()
        snapshot.append("sentinel")
        self.assertEqual(len(engine.last_results()), 1)

    def test_clear(self):
        engine = HookEngine()
        engine.register(_hook("a"))
        engine.fire(HookEvent.PRE_TOOL)
        engine.clear()
        self.assertEqual(engine.hooks(), [])
        self.assertEqual(engine.preview(HookEvent.PRE_TOOL), [])
        self.assertEqual(engine.last_results(), [])


class TestBudget(unittest.TestCase):

    def test_exceeding_budget_raises_before_running(self):
        engine = HookEngine(max_hooks=2)
        recs = []
        for i in range(3):
            rec = _Recorder()
            recs.append(rec)
            engine.register(_hook("h%d" % i, callback=rec))
        with self.assertRaises(HookBudgetError):
            engine.fire(HookEvent.PRE_TOOL)
        self.assertEqual([r.calls for r in recs], [[], [], []])

    def test_disabled_hooks_do_not_count_against_budget(self):
        engine = HookEngine(max_hooks=1)
        engine.register(_hook("a", display_order=0))
        engine.register(_hook("b", display_order=1))
        engine.disable("b")
        results = engine.fire(HookEvent.PRE_TOOL)
        self.assertEqual([r.hook for r in results], ["a"])

    def test_at_budget_runs(self):
        engine = HookEngine(max_hooks=2)
        engine.register(_hook("a", display_order=0))
        engine.register(_hook("b", display_order=1))
        self.assertEqual(len(engine.fire(HookEvent.PRE_TOOL)), 2)

    def test_invalid_budget_value(self):
        with self.assertRaises(ValueError):
            HookEngine(max_hooks=0)
        with self.assertRaises(ValueError):
            HookEngine(max_hooks=True)


class TestHookResultShape(unittest.TestCase):

    def test_result_fields_and_immutability(self):
        engine = HookEngine()
        engine.register(_hook("a"))
        result = engine.fire(HookEvent.PRE_TOOL)[0]
        self.assertIsInstance(result, HookResult)
        self.assertEqual(result.event, HookEvent.PRE_TOOL)
        self.assertEqual(result.duration_s, 0.0)
        with self.assertRaises(Exception):
            result.ok = False

    def test_injected_timer_sets_duration(self):
        ticks = iter([10.0, 10.5])
        engine = HookEngine(timer=lambda: next(ticks))
        engine.register(_hook("a"))
        result = engine.fire(HookEvent.PRE_TOOL)[0]
        self.assertAlmostEqual(result.duration_s, 0.5)


if __name__ == "__main__":
    unittest.main()
